"""Move an equal final-answer CE allocation from valid to corrupted carry prefixes."""

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
from time import monotonic, time
from unittest.mock import patch

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_calculation_prefix_cpu as calc
from scripts import diag_p109c_conditional_margin_cpu as shared


REF, PRIOR = shared.REF, shared.prior
OUT = REF.EVIDENCE / "p109c_arithmetic_recovery_cpu_20261126"
END = datetime.fromisoformat("2026-11-26T14:00:00+09:00")
STEPS, AUXILIARY = 32, .20
ARMS = {"verified_aux": 0, "recovery_aux": 1}
GROUPS = (("ko", 0), ("en", 0), ("ko", 1), ("en", 1))


def compatible_cases(tokenizer, source_rows):
    for source in source_rows:
        meta = source["meta"]
        if meta["family"] != "addition" or min(meta["task"]["a"], meta["task"]["b"]) < 10:
            continue
        if meta["split"] == "dev" and meta["view"] != 2 * (int(meta["root"][-1], 16) % 2):
            continue
        mapped = dict(source, messages=[dict(role=row["role"], content=[{"text": row["content"]}])
                                        for row in source["messages"]])
        case = calc.variants(tokenizer, mapped)
        if case is not None:
            yield case


def encode_case(tokenizer, case):
    marker = "답: " if case["language"] == "ko" else "Answer: "
    answer = marker + str(case["expected"])
    prompt = calc.BASE.serialize({"messages": [{"role": "user", "content": case["question"]}]},
                                 "chatml", add_generation_prompt=True)
    start = len(case["inputs"]["free"])-1
    rows, tails = [], []
    for family in ("verified_steps", "wrong_carry"):
        prefix = case["inputs"][family]
        content = tokenizer.encode(prompt + case["prefixes"][family] + answer).ids
        if content[:len(prefix)] != prefix or len(content) == len(prefix):
            raise ValueError("the final answer must extend the shared complete prefix")
        final = content[len(prefix):] + [PRIOR.EOT]
        tails.append(final)
        rows.append((content + [PRIOR.EOT], start, len(content)-start-1, family == "verified_steps"))
    if tails[0] != tails[1] or rows[0][2] != rows[1][2]:
        raise ValueError("the proposed supervision move must preserve every token and amount")
    return rows, len(tails[0])


def select(tokenizer):
    corpus = calc.verifier.build_course()
    train = defaultdict(list)
    for row in compatible_cases(tokenizer, corpus["train"]["trace"]):
        train[row["language"], row["carry"]].append(row)
    need = STEPS * PRIOR.ACCUM
    groups = [sorted(train[key], key=lambda row: PRIOR.json_digest(["recovery", row["id"]]))[:need] for key in GROUPS]
    if any(len(group) != need for group in groups):
        raise ValueError("both languages and carry cases must fill every fixed batch")
    panel = [row for step in zip(*groups, strict=True) for row in step]

    dev = defaultdict(dict)
    for case in compatible_cases(tokenizer, corpus["dev"]["trace"]):
        dev[case["id"]][case["language"]] = case
    groups = {0: [], 1: []}
    for root in sorted(dev):
        cases = dev[root]
        if set(cases) == {"ko", "en"} and len(groups[cases["ko"]["carry"]]) < 8:
            groups[cases["ko"]["carry"]].append(cases)
    if any(len(group) != 8 for group in groups.values()):
        raise ValueError("the DEV evaluation must have eight roots per carry condition")
    hold = [item[lang] for group in groups.values() for item in group for lang in ("ko", "en")]
    test_path = calc.OUT / "inputs.json"
    test_roots = {case["id"] for case in REF.completed.read_json(test_path)["cases"]}
    if {row["id"] for row in panel} & (test_roots | set(dev)) or test_roots & set(dev):
        raise ValueError("the training, earlier TEST and new DEV roots overlap")
    return panel, hold, corpus["report"]["root_ids_sha256"]


def update(model, group, replay, offset):
    rows = [row for packed, _ in group for row in packed]
    head, captured = model._head_logits, []

    def keep(hidden):
        logits = head(hidden)
        captured.append(logits)
        return logits

    with patch.object(model, "_head_logits", keep):
        ce, raw, _, _, _, totals = shared.update_batch(model, rows, replay)
    if len(captured) != 1:
        raise ValueError("the answer must come from the same output table projection")
    positions, labels = [], []
    cursor = 0
    for pair, end_count in group:
        answer_width = pair[0][2] + 1
        end = cursor + (offset+1) * answer_width
        positions.extend(range(end-end_count, end))
        labels.extend(pair[offset][0][-end_count:])
        cursor += 2 * answer_width
    aux = F.cross_entropy(captured[0][positions].float(), torch.tensor(labels))
    return ce, raw, aux, dict(totals, auxiliary_targets=len(labels))


def ensure_time(cutoff):
    if time() >= cutoff:
        raise TimeoutError("the two-arm recovery validation reached the approved cutoff")


def train(model, arm, encoded, replay, profile, cutoff):
    model.clear_quant()
    model.cfg.infer_repeat = 1.
    model.train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("training and evaluation must remain on native R2")
    optimizer = torch.optim.AdamW(model.parameters(), lr=profile["lr"], weight_decay=0., foreach=False)
    totals = dict.fromkeys(profile["exposure"], 0)
    begin = monotonic()
    with (OUT / f"{arm}_updates.jsonl").open("x", encoding="utf-8", buffering=1) as log:
        for step in range(STEPS):
            ensure_time(cutoff)
            optimizer.zero_grad(set_to_none=True)
            measurements = []
            for micro in range(PRIOR.ACCUM):
                index = step*PRIOR.ACCUM + micro
                ce, raw, aux, observed = update(model, encoded[index*4:index*4+4],
                                                replay[index*2:index*2+2], ARMS[arm])
                ((ce + profile["replay_weight"]*raw + AUXILIARY*aux)/PRIOR.ACCUM).backward()
                measurements.append([float(value.detach()) for value in (ce, raw, aux)])
                for key in totals:
                    totals[key] += observed[key]
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            row = dict(arm=arm, step=step+1, seconds=monotonic()-begin, loss=measurements,
                       grad_norm=float(norm), exposure=totals)
            print(json.dumps(row), file=log)
            if step == 0 or (step+1) % 8 == 0:
                print(json.dumps(row), flush=True)
    if totals != profile["exposure"]:
        raise ValueError("the actual monitored supervision differs from the shared input trace")
    model.eval()
    model.cfg.infer_repeat = 2.
    with torch.no_grad():
        model.freeze_quant()
    return totals


@torch.inference_mode()
def assess(model, tokenizer, holdout, val, cutoff):
    rows = []
    for case in holdout:
        for arm in ("free", "verified_steps", "wrong_carry"):
            ensure_time(cutoff)
            rows.append(calc.generate(model, tokenizer, case, arm))
    raw = PRIOR.assess(model, tokenizer, [], [], val, cutoff)
    measured = calc.summarize(rows)
    measured.pop("first_step")
    return dict(rows=rows, summary=measured, raw_nll=raw["raw_val_nll"], raw_windows=raw["raw_val_windows"])


def compare(a, b, parent_nll):
    old, new = (value["summary"] for value in (a, b))
    gain = {lang: new["wrong_carry"][lang]["correct_end"] - old["wrong_carry"][lang]["correct_end"]
            for lang in ("all", "ko", "en")}
    delta = b["raw_nll"] - parent_nll
    return dict(gain=gain, raw_delta=delta, gates=dict(
        recovery=gain["all"] >= 8 and all(gain[lang] >= 2 for lang in ("ko", "en")),
        valid=all(new[condition]["all"][metric] >= old[condition]["all"][metric]-1
                  for condition, metric in (("verified_steps", "correct_end"), ("free", "correct_end"),
                                            ("free", "valid_trace"))),
        original=delta <= .005))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 only after the paired fixed raw validation has returned")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    old, tokenizer, checkpoint, _, _, _, replay, val = shared.prepare()
    base_report = REF.completed.read_json(shared.OUT / "report.json")
    if (old != REF.completed.read_json(shared.PROFILE) or base_report["status"] != "COMPLETE"
            or base_report["profile_sha256"] != REF.file_sha(shared.PROFILE)):
        raise ValueError("the original v3, validation and replay must agree with the previous completed comparison")
    panel, hold, corpus_sha = select(tokenizer)
    encoded = [encode_case(tokenizer, case) for case in panel]
    replay = replay[:STEPS*PRIOR.ACCUM*2]
    totals = dict(inputs=sum(len(row[0])-1 for pair, _ in encoded for row in pair) + len(replay)*PRIOR.REPLAY_WIDTH,
                  answer_targets=sum(pair[0][2]+1 for pair, _ in encoded), auxiliary_targets=sum(n for _, n in encoded),
                  replay_targets=len(replay)*PRIOR.REPLAY_WIDTH)
    profile = dict(parent_sha256=old["parent_sha256"], corpus_root_sha256=corpus_sha,
                   training_cases=panel, held_cases=hold, exposure=totals, source_sha256=REF.file_sha(Path(__file__)),
                   shared_input_sha256=REF.file_sha(shared.PROFILE), replay_sha256=PRIOR.json_digest(replay.tolist()),
                   lr=old["lr"], replay_weight=old["replay_weight"], auxiliary_weight=AUXILIARY,
                   steps=STEPS, arms=ARMS)
    OUT.mkdir(exist_ok=False)
    inputs = OUT / "inputs.json"
    REF.native.publish(inputs, profile)
    summaries = {}
    cutoff = args.stop_by.timestamp()
    with sdpa_kernel(SDPBackend.MATH):
        for arm in ARMS:
            ensure_time(cutoff)
            torch.manual_seed(old["seed"])
            model = REF.completed.load_model(checkpoint, 2942, "cpu")
            observed = train(model, arm, encoded, replay, profile, cutoff)
            result = assess(model, tokenizer, hold, val, cutoff)
            REF.native.publish(OUT / f"{arm}_assessment.json", dict(training=observed, **result))
            summaries[arm] = {key: result[key] for key in ("summary", "raw_nll")}
            if arm == "verified_aux":
                del model
    if REF.file_sha(checkpoint) != old["parent_sha256"]:
        raise ValueError("the shared base body changed")
    comparison = compare(*summaries.values(), base_report["parent_raw_nll"])
    eligible_body = None
    if all(comparison["gates"].values()):
        ensure_time(cutoff)
        body = OUT / "recovery_aux_body.pt"
        with body.open("xb") as stream:
            torch.save(dict(schema="P109C_ARITHMETIC_RECOVERY_V1", parent_sha256=old["parent_sha256"],
                            inputs_sha256=REF.file_sha(inputs), model=model.state_dict()), stream)
        eligible_body = dict(path=body.name, sha256=REF.file_sha(body))
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=REF.file_sha(inputs), arms=summaries,
                                                parent_nll=base_report["parent_raw_nll"], comparison=comparison,
                                                eligible_body=eligible_body))
    print("P109C_ARITHMETIC_RECOVERY", json.dumps(comparison), flush=True)


if __name__ == "__main__":
    main()
