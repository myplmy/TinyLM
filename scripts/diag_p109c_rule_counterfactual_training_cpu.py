"""Compare answer CE against the same P109C post-training with paired rule supervision."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from random import Random
import resource
from time import monotonic, time

import numpy as np
import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_rule_label_position_cpu as rule
from scripts import diag_p109c_v3_rule_flip as reference
from scripts import eval_p109b_first_use as decode
from scripts import interactive_research_infer as manual
from scripts import p109c_rule_counterfactual_cases as fixture
from scripts import run_p109c_integrated_scratch as integrated
from tinylm.infer.generate import sample


TAG = "p109c_paired_rule_cpu_20261125"
PROFILE = reference.EVIDENCE / f"{TAG}_profile.json"
RECORD = reference.EVIDENCE / TAG
CPUS = set(range(14))
THREADS = 7
STEPS = 64
ACCUM = 2
ROWS = 10
WIDTH = 256
REPLAY_WIDTH = 96
END = datetime.fromisoformat("2026-11-25T13:00:00+09:00")
ARMS = {"ce": 0., "paired": .10}
EOT = 4


def json_digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest().upper()


def prepare():
    tokenizer = reference.completed.load_tokenizer()
    checkpoint = reference.checkpoint()
    curriculum, bundle, _, _ = integrated.prepare("original", "capped", "proportional", 0., True)
    train = fixture.make_cases(fixture.TRAIN, 16, 1762251)
    holdout = fixture.make_cases(fixture.HOLDOUT, 5, 1762253)
    original = [{**row, "prompts": [row["evidence"].format(value=row[key]) + "\n" + row["question"] + "\n"
                                    + rule.instructions(row["language"])[1] for key in ("yes", "no")]}
                for row in reference.panel()]
    if (len(train) != STEPS * ACCUM * 2 or len(holdout) != 40
            or {row["family"] for row in train} & {row["family"] for row in holdout}
            or len({p for row in train + holdout for p in row["prompts"]}) != 2 * (len(train) + len(holdout))
            or {row["question"] for row in train} & {row["question"] for row in holdout + original}):
        raise ValueError("the new rule families or held-out prompts overlap")
    replay_ids = Random(1762259).sample(range(len(bundle.starts)), STEPS * ACCUM * 2)
    replay = bundle.raw_batch(np.array(replay_ids))[:, 0, :REPLAY_WIDTH + 1]
    val = np.memmap(integrated.prep.CACHE / "val.bin", dtype="<u2", mode="r")
    starts = Random(1762261).sample(range(len(val) - 257), 24)
    validation = [val[start:start + 257].astype(np.int64).tolist() for start in starts]
    pins = {path.name: reference.file_sha(path) for path in (Path(__file__), Path(fixture.__file__),
            Path(rule.__file__), Path(reference.__file__), Path(integrated.__file__))}
    profile = dict(tag=TAG, sources=pins, parent_sha256=reference.CHECKPOINT_SHA256,
                   tokenizer_sha256=reference.completed.TOKENIZER_SHA, layout=curriculum["signature"]["layout"],
                   raw_input=curriculum["signature"]["raw"], train_pairs=len(train), holdout_pairs=len(holdout),
                   train_sha256=json_digest(train), holdout_sha256=json_digest(holdout), original_sha256=json_digest(original),
                   replay_ids_sha256=json_digest(replay_ids), replay_sha256=json_digest(replay.tolist()),
                   val_sha256=json_digest(validation), val_tokens=len(validation) * 256,
                   steps=STEPS, accum=ACCUM, rows=ROWS, width=WIDTH, reserved=STEPS * ACCUM * ROWS * WIDTH,
                   cpu_affinity=sorted(CPUS), threads=THREADS, lr=0.00002, replay_weight=.20, arms=ARMS)
    bundle.unchanged()
    return profile, tokenizer, checkpoint, train, holdout, original, replay, validation


def encoded_pair(tokenizer, item):
    out = []
    labels = reference.LABELS[item["language"]]
    for case_index, text in enumerate(item["prompts"]):
        prefix, continuations = rule.continuations(tokenizer, rule.chat(text), labels)
        for label_index, answer in enumerate(continuations):
            out.append((prefix + answer + [EOT], len(prefix) - 1, len(answer), case_index == label_index))
    return out


def update_batch(model, paired_rows, replay):
    rows = [*paired_rows, *((r.tolist(), 0, 0, False) for r in replay)]
    width = max(len(tokens) - 1 for tokens, _, _, _ in rows)
    if len(rows) != ROWS or not 1 <= width <= WIDTH:
        raise ValueError("the real post-training microbatch exceeds the sealed shape")
    wire = torch.zeros((ROWS, width), dtype=torch.long)
    indices, positions, targets, ce, body = [], [], [], [], []
    for i, (tokens, start, body_length, positive) in enumerate(rows):
        wire[i, :len(tokens) - 1] = torch.tensor(tokens[:-1])
        for j in range(start, len(tokens) - 1):
            indices.append(i)
            positions.append(j)
            targets.append(tokens[j + 1])
            ce.append(positive)
            body.append(j < start + body_length)
    hidden = model(wire, return_hidden=True)
    index = torch.tensor(indices)
    logits = model._head_logits(hidden[index, positions]).float()
    logp = logits.log_softmax(dim=-1).gather(1, torch.tensor(targets)[:, None]).flatten()
    per_answer = logp.new_zeros(ROWS).index_add(0, index, logp * torch.tensor(body))[:8].reshape(2, 4)
    margins = per_answer[:, 0] - per_answer[:, 1] - per_answer[:, 2] + per_answer[:, 3]
    valid = torch.tensor(ce)
    return (-logp[valid].mean(), -logp[index >= 8].mean(), F.softplus(1 - margins).mean(),
            dict(inputs=sum(len(data[0]) - 1 for data in rows), answer_targets=sum(ce),
                 replay_targets=len(replay) * REPLAY_WIDTH, fact_margin=float(margins.detach().mean())))


def check(deadline):
    if time() >= deadline or (RECORD / "STOP").exists():
        raise TimeoutError("the CPU learning diagnostic reached the approved end")


def greedy(model, tokenizer, language, text):
    prompt = rule.chat(text)
    ids = tokenizer.encode(prompt).ids
    capture = decode.DecodeSuffix(tokenizer, ids)
    _, metadata = sample(model, model.cfg, capture, prompt, max_new=32, temperature=0., top_k=1,
                         device="cpu", eos_id=2, use_cache=True, logits_last_only=True,
                         return_metadata=True, stop_token_sequences=[[EOT]])
    answer, metadata = manual.answer_from_tokens(tokenizer, ids, ids + capture.ids, metadata, 32)
    return dict(answer=answer, label=reference.score_label(answer, language),
                stopped=metadata["finish_reason"], ids=metadata["generated_ids"])


@torch.inference_mode()
def assess(model, tokenizer, holdout, original, validation, deadline):
    result = {}
    for name, cases in (("new_rules", holdout), ("previous_dev", original)):
        rows = []
        for item in cases:
            check(deadline)
            yes, no = [greedy(model, tokenizer, item["language"], text) for text in item["prompts"]]
            rows.append(dict(id=item["id"], language=item["language"], yes=yes, no=no,
                             correct=yes["label"] == "yes" and no["label"] == "no"))
        result[name] = dict(rows=rows, counts={lang: sum(r["correct"] for r in rows if lang == "all" or r["language"] == lang)
                                               for lang in ("all", "en", "ko")})
    nll = []
    for start in range(0, len(validation), 2):
        check(deadline)
        rows = torch.tensor(validation[start:start+2])
        hidden = model(rows[:, :-1], return_hidden=True)
        losses = F.cross_entropy(model._head_logits(hidden).transpose(1, 2).float(), rows[:, 1:], reduction="none")
        nll.extend(losses.mean(1).tolist())
    result["raw_val_nll"] = sum(nll) / len(nll)
    result["raw_val_windows"] = nll
    return result


def train_arm(arm, profile, model, encoded, replay, deadline):
    model.clear_quant()
    model.cfg.infer_repeat = 1.
    model.train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the original v3 R2 route differs")
    optimizer = torch.optim.AdamW(model.parameters(), lr=profile["lr"], weight_decay=0., foreach=False)
    reports = []
    start = monotonic()
    totals = {"inputs": 0, "answer_targets": 0, "replay_targets": 0}
    with (RECORD / f"{arm}_updates.jsonl").open("x", encoding="utf-8", buffering=1) as log:
        for step in range(STEPS):
            check(deadline)
            optimizer.zero_grad(set_to_none=True)
            values = []
            for micro in range(ACCUM):
                i = 2 * (step * ACCUM + micro)
                pair_rows = encoded[i] + encoded[i + 1]
                ce, text, rank, observed = update_batch(model, pair_rows, replay[i:i + 2])
                ((ce + profile["replay_weight"]*text + ARMS[arm]*rank) / ACCUM).backward()
                for key in totals:
                    totals[key] += observed[key]
                values.append((float(ce.detach()), float(text.detach()), float(rank.detach()), observed["fact_margin"]))
            norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True))
            optimizer.step()
            entry = dict(arm=arm, step=step+1, elapsed=monotonic()-start, ce=np.mean(values, axis=0).tolist(), grad_norm=norm)
            print(json.dumps(entry), file=log)
            if step == 0 or (step + 1) % 8 == 0:
                print(json.dumps(entry), flush=True)
            reports.append(entry)
    if totals["replay_targets"] != STEPS * ACCUM * 2 * REPLAY_WIDTH:
        raise ValueError("the observed replay differs from the sealed exposure")
    elapsed = monotonic()-start
    model.eval()
    model.cfg.infer_repeat = 2.
    with torch.no_grad():
        model.freeze_quant()
    destination = RECORD / f"{arm}_body.pt"
    with destination.open("xb") as stream:
        torch.save(dict(schema="P109C_CPU_PAIRED_RULE_DIAGNOSTIC", parent_sha256=profile["parent_sha256"], arm=arm,
                        post_updates=STEPS, model=model.state_dict()), stream)
    return dict(totals=totals, elapsed_s=elapsed, peak_process_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                body_sha256=reference.file_sha(destination), final_update=reports[-1])


def run(profile, tokenizer, checkpoint, train, holdout, original, replay, validation, deadline):
    torch.set_num_threads(THREADS)
    torch.set_num_interop_threads(1)
    torch.manual_seed(1337)
    RECORD.mkdir(exist_ok=False)
    encoded = [encoded_pair(tokenizer, item) for item in train]
    expected_answer_targets = sum(length + 1 for pair in encoded for _, _, length, reward in pair if reward)
    expected_inputs = sum(len(row[0]) - 1 for pair in encoded for row in pair) + STEPS * ACCUM * 2 * REPLAY_WIDTH
    comparison = {}
    with sdpa_kernel(SDPBackend.MATH):
        baseline = reference.completed.load_model(checkpoint, 2942, "cpu")
        baseline_report = assess(baseline, tokenizer, holdout, original, validation, deadline)
        reference.native.publish(RECORD / "baseline.json", baseline_report)
        del baseline
        for arm in ARMS:
            check(deadline)
            torch.manual_seed(1337)
            model = reference.completed.load_model(checkpoint, 2942, "cpu")
            training = train_arm(arm, profile, model, encoded, replay, deadline)
            if training["totals"]["answer_targets"] != expected_answer_targets or training["totals"]["inputs"] != expected_inputs:
                raise ValueError("the actual paired answers or inputs differ from the frozen schedule")
            assessment = assess(model, tokenizer, holdout, original, validation, deadline)
            comparison[arm] = dict(training=training, assessment=assessment)
            reference.native.publish(RECORD / f"{arm}_assessment.json", comparison[arm])
            del model
    if reference.file_sha(checkpoint) != profile["parent_sha256"]:
        raise ValueError("the original evaluated model changed during training")
    scores = {}
    for name in ("new_rules", "previous_dev"):
        ce, paired = (comparison[arm]["assessment"][name] for arm in ARMS)
        scores[name] = dict(baseline=baseline_report[name]["counts"], ce=ce["counts"], paired=paired["counts"],
                            wins=sum(b["correct"] and not a["correct"] for a, b in zip(ce["rows"], paired["rows"], strict=True)),
                            losses=sum(a["correct"] and not b["correct"] for a, b in zip(ce["rows"], paired["rows"], strict=True)))
    result = dict(status="COMPLETE", profile=profile, baseline_raw=baseline_report["raw_val_nll"], summary=scores,
                  raw_val={arm: comparison[arm]["assessment"]["raw_val_nll"] for arm in ARMS},
                  training={arm: comparison[arm]["training"] for arm in ARMS})
    reference.native.publish(RECORD / "report.json", result)
    print(json.dumps(scores, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.sched_getaffinity(0) != CPUS or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("use the pinned CPU-only path while keeping CPU 14 clear for context measurements")
    profile, *assets = prepare()
    if args.action == "prepare":
        reference.native.publish(PROFILE, profile)
        print(reference.file_sha(PROFILE), flush=True)
        return 0
    if (args.stop_by is None or args.stop_by.tzinfo is None or args.stop_by > END or time() >= args.stop_by.timestamp()
            or args.profile_sha256 != reference.file_sha(PROFILE) or profile != reference.completed.read_json(PROFILE)):
        parser.error("the fixed training and evaluation profile must match a live authorized CPU interval")
    run(profile, *assets, args.stop_by.timestamp())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
