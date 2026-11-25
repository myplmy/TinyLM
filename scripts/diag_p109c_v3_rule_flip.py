"""Frozen development diagnosis of evidence and answer production in P109C v3."""

from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

from scripts import eval_p109c_completed as completed
from scripts import eval_p109c_mixed_v2 as mixed
from scripts import p109_eval_resilient_supervisor as supervisor
from scripts import run_p109c_scratch330 as native
from tinylm.chat.serialize import serialize


TAG = "p109c_v3_rule_flip_20261124"
EVIDENCE = completed.ROOT / "test_result/evidence"
INPUT = EVIDENCE / f"{TAG}_inputs.jsonl"
PROFILE = EVIDENCE / f"{TAG}_profile.json"
TRAINING = EVIDENCE / "p109c_integrated_scratch_v3_v11_chat32_s1337_run1_20261124"
CHECKPOINT_SHA256 = "8556E8A3F998B378B330667A66BA379BD2CECD79523B7D4197E02CA5F920A94A"
AUTHORIZED_END = datetime.fromisoformat("2026-11-25T01:00:00+09:00")
CPU_SET = set(range(8))
CARD_MIB = 6144
MAX_NEW = 96
LABELS = {"en": ("Yes", "No"), "ko": ("예", "아니요")}


def file_sha(path):
    return completed.core6.digest(path).upper()


def checkpoint():
    receipt = completed.read_json(TRAINING / "input.json")
    with patch.object(mixed.native, "STEPS", 2942):
        path, stamp = mixed.completed_v2(TRAINING, receipt["manifest_sha256"])
    if stamp.upper() != CHECKPOINT_SHA256:
        raise ValueError("the completed v3 evaluation body differs from the approved asset")
    return path


def panel():
    rows = [json.loads(line) for line in INPUT.read_text(encoding="utf-8").splitlines()]
    groups = Counter((row["language"], row["kind"]) for row in rows)
    if (groups != Counter({(language, kind): 10 for language in LABELS for kind in ("single", "composed")})
            or len({row["id"] for row in rows}) != 40 or len({row["question"] for row in rows}) != 40
            or any(row["evidence"].count("{value}") != 1 or row["yes"] == row["no"] for row in rows)):
        raise ValueError("the admitted panel needs 40 distinct pairs with one changed value")
    return rows


def prompts(tokenizer, rows):
    def chat(text):
        return serialize({"messages": [{"role": "user", "content": text}]}, "chatml", add_generation_prompt=True)

    cases = []
    for index, row in enumerate(rows):
        language = row["language"]
        answer_instruction = "Answer only Yes or No." if language == "en" else "예 또는 아니요만 쓰세요."
        order_instruction = "Write only A or B." if language == "en" else "A 또는 B만 쓰세요."
        for gold in (("yes", "no") if index % 2 == 0 else ("no", "yes")):
            evidence = row["evidence"].format(value=row[gold])
            full = "\n\n".join((row["before"], evidence, row["after"]))
            query = "\n\n" + row["question"] + "\n"
            free = [chat(context + query + answer_instruction) for context in (full, evidence)]
            choice = []
            for order in (("yes", "no"), ("no", "yes")):
                names = dict(zip(("yes", "no"), LABELS[language], strict=True))
                prompt = chat(evidence + query + f"A. {names[order[0]]}\nB. {names[order[1]]}\n" + order_instruction)
                ids = tokenizer.encode(prompt).ids
                candidates = [tokenizer.encode(prompt + label).ids for label in ("A", "B")]
                if (any(tokens[:-1] != ids for tokens in candidates)
                        or candidates[0][-1] == candidates[1][-1]):
                    raise ValueError(f"{row['id']} does not have two distinct one-token candidate continuations")
                choice.append(dict(prompt=prompt, ids=ids, order=order, tokens=[tokens[-1] for tokens in candidates]))
            if max(len(tokenizer.encode(value).ids) + MAX_NEW for value in free) > 1024:
                raise ValueError(f"{row['id']} would truncate its free-generation request")
            cases.append(dict(id=row["id"], language=language, kind=row["kind"], gold=gold,
                              evidence=evidence, free=free, choice=choice))
    return cases


def overlap_check(tokenizer, rows):
    import numpy as np
    from scripts import p106b_final_holdout as final
    from scripts import run_p109c_integrated_scratch as integrated

    normalized = integrated.prep.normalize_text
    frozen = [normalized(item["prompt"]) for split in ("dev", "final") for item in final.build(split)]
    questions = {row["id"]: normalized(row["question"]) for row in rows}
    if any(question in prior for question in questions.values() for prior in frozen):
        raise ValueError("the new panel overlaps a frozen development or final evaluation prompt")
    admitted, bundle, _, _ = integrated.prepare("original", "capped", "proportional", 0., True)
    searched_rows = 0
    fragments = {}
    for row in rows:
        # Use literal interior tokens so an incidental leading/trailing BPE merge cannot hide a match.
        strings = [row["question"], *(row["evidence"].format(value=row[key]) for key in ("yes", "no"))]
        fragments[row["id"]] = [tokenizer.encode(value).ids[1:-1] for value in strings]
    for lane in bundle.data:
        inputs = lane[:, :, 0, :].reshape(-1, integrated.prep.WIDTH)
        searched_rows += len(inputs)
        for name, needles in fragments.items():
            for needle in needles:
                if len(needle) < 3:
                    raise ValueError("an overlap check needs at least three literal interior tokens")
                middle = len(needle) // 2
                row_ids, cols = np.nonzero(inputs[:, middle : inputs.shape[1] - len(needle) + middle + 1] == needle[middle])
                live = np.ones(len(cols), dtype=bool)
                for offset, token in enumerate(needle):
                    if offset == middle:
                        continue
                    live &= inputs[row_ids, cols + offset] == token
                    if not live.any():
                        break
                if live.any():
                    raise ValueError(f"{name} matches an admitted curriculum token span")
    bundle.unchanged()
    return dict(frozen_prompts=len(frozen), curriculum_packed_rows=searched_rows,
                curriculum_layout=admitted["signature"]["layout"], literal_hits=0,
                scope="Normalized frozen prompts and literal interior Chat32 spans in all adopted packed lanes.")


def pins():
    sources = mixed.pinned_sources()
    for path in (Path(__file__).resolve(), Path(supervisor.__file__).resolve(), INPUT):
        sources[str(path.relative_to(completed.ROOT))] = file_sha(path)
    return sources


def make_profile():
    tokenizer = completed.load_tokenizer()
    rows = panel()
    cases = prompts(tokenizer, rows)
    proof = overlap_check(tokenizer, rows)
    model = checkpoint()
    native.publish(PROFILE, dict(tag=TAG, source_sha256=pins(), input_sha256=file_sha(INPUT),
                   cases_sha256=sha256(json.dumps(cases, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                   checkpoint=str(model.relative_to(completed.ROOT)), checkpoint_sha256=CHECKPOINT_SHA256,
                   cases=len(cases), max_new=MAX_NEW, card_ceiling_mib=CARD_MIB, cpu_affinity=sorted(CPU_SET),
                   overlap=proof, primary="Both responses correct; candidate scoring must pass both option orders.",
                   secondary="Same recognized answer, first-label and strict answer, empty, repeat, cap, candidate margins."))
    print(f"SEALED {PROFILE} {file_sha(PROFILE)} cases={len(cases)}", flush=True)


def score_label(text, language, *, first=False):
    import re

    text = text.strip().casefold()
    labels = {"yes": "yes", "no": "no"} if language == "en" else {
        "예": "yes", "네": "yes", "아니요": "no", "아니오": "no"}
    if first:
        text = re.split(r"[\s.!?。！？,:]+", text, maxsplit=1)[0]
    return labels.get(text.strip(".!?。！？"))


def generate(model, tokenizer, prompt, language):
    from scripts import eval_p109b_first_use as first
    from scripts import interactive_research_infer as manual
    from tinylm.infer.generate import sample

    ids = tokenizer.encode(prompt).ids
    capture = first.DecodeSuffix(tokenizer, ids)
    _, metadata = sample(model, model.cfg, capture, prompt, max_new=MAX_NEW, temperature=0., top_k=1,
                         device="cuda", eos_id=2, use_cache=True, logits_last_only=True,
                         return_metadata=True, stop_token_sequences=[[4]])
    answer, metadata = manual.answer_from_tokens(tokenizer, ids, ids + capture.ids, metadata, MAX_NEW)
    return dict(prompt=prompt, answer=answer, label=score_label(answer, language),
                first_label=score_label(answer, language, first=True), metadata=metadata,
                empty=not answer.strip(), repeat=first.repeat_tail(metadata["generated_ids"]),
                cap=metadata["finish_reason"] == "MAX_NEW")


def choose(model, spec, torch):
    value = torch.tensor([spec["ids"]], dtype=torch.long, device="cuda")
    hidden = model(value, return_hidden=True)
    logits = model._head_logits(hidden[:, -1]).float()[0]
    scores = logits.log_softmax(-1)[spec["tokens"]].tolist()
    if not all(math.isfinite(score) for score in scores):
        raise ValueError("the sealed candidate score is nonfinite")
    by_answer = dict(zip(spec["order"], scores, strict=True))
    margin = by_answer["yes"] - by_answer["no"]
    decision = "yes" if margin > 0 else "no" if margin < 0 else None
    return dict(prompt=spec["prompt"], order=spec["order"], token_ids=spec["tokens"],
                log_probability=by_answer, yes_minus_no=margin, label=decision)


def summary(rows):
    pairs = {}
    for row in rows:
        pairs.setdefault(row["id"], {})[row["gold"]] = row
    result = {}
    for language in ("all", "ko", "en", "single", "composed"):
        subset = [sides for sides in pairs.values() if language in ("all", sides["yes"]["language"], sides["yes"]["kind"])]
        metrics = Counter(pairs=len(subset))
        for sides in subset:
            good = {}
            for condition in ("full", "evidence", "candidate"):
                a, b = (sides[label][condition] for label in ("yes", "no"))
                good[condition] = a["label"] == "yes" and b["label"] == "no"
                metrics.update({f"{condition}_pair_correct": good[condition],
                                f"{condition}_same_label": a["label"] is not None and a["label"] == b["label"],
                                f"{condition}_correct_items": int(a["label"] == "yes") + (b["label"] == "no")})
                if condition != "candidate":
                    for key in ("empty", "repeat", "cap"):
                        metrics[f"{condition}_{key}"] += a[key] + b[key]
                    metrics[f"{condition}_unrecognized"] += (a["label"] is None) + (b["label"] is None)
                    metrics[f"{condition}_first_label_pair_correct"] += a["first_label"] == "yes" and b["first_label"] == "no"
                else:
                    for order in (0, 1):
                        metrics[f"candidate_order_{order}_pair_correct"] += (
                            a["orders"][order]["label"] == "yes" and b["orders"][order]["label"] == "no")
                    for row in (a, b):
                        metrics["candidate_order_disagreement"] += row["orders"][0]["label"] != row["orders"][1]["label"]
                        metrics["candidate_first_option_choices"] += sum(
                            choice["label"] == choice["order"][0] for choice in row["orders"])
                    metrics["candidate_margin_direction_same_both_orders"] += all(
                        a["orders"][order]["yes_minus_no"] > b["orders"][order]["yes_minus_no"] for order in (0, 1))
            for baseline, challenger in (("full", "evidence"), ("evidence", "candidate")):
                key = f"{challenger}_vs_{baseline}"
                metrics[f"{key}_wins"] += good[challenger] and not good[baseline]
                metrics[f"{key}_losses"] += good[baseline] and not good[challenger]
        result[language] = dict(metrics)
    return result


def worker(path, stamp, _resume, record, cutoff):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    sealed = json.loads(native.manifest_bytes(path, stamp))
    tokenizer = completed.load_tokenizer()
    cases = prompts(tokenizer, panel())
    encoded = json.dumps(cases, ensure_ascii=False, sort_keys=True).encode()
    if (sealed["source_sha256"] != pins() or sealed["cases_sha256"] != sha256(encoded).hexdigest()
            or os.sched_getaffinity(0) != CPU_SET or torch.cuda.device_count() != 1):
        raise ValueError("the sealed task, CPU mask or assigned GPU differs")
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    free, total = torch.cuda.mem_get_info()
    allowed = (CARD_MIB - 640) * 2**20 - (total - free)
    if not 0 < allowed < total:
        raise ValueError("the card has no room in the approved envelope")
    torch.cuda.set_per_process_memory_fraction(allowed / total)
    started = time.monotonic()
    torch.cuda.reset_peak_memory_stats()
    model = completed.load_model(checkpoint(), 2942, "cuda")
    results = []
    global_peak = 0
    with (torch.inference_mode(), sdpa_kernel(SDPBackend.MATH),
          (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress,
          (record / "answers.jsonl").open("x", encoding="utf-8", buffering=1) as output):
        for case in cases:
            if time.time() >= cutoff:
                raise TimeoutError("the approved inference window ended")
            full, evidence = [generate(model, tokenizer, prompt, case["language"]) for prompt in case["free"]]
            orders = [choose(model, spec, torch) for spec in case["choice"]]
            consistent = orders[0]["label"] if orders[0]["label"] == orders[1]["label"] else None
            result = {key: case[key] for key in ("id", "language", "kind", "gold")}
            result.update(passage=case["evidence"], full=full, evidence=evidence,
                          candidate=dict(label=consistent, orders=orders))
            print(json.dumps(result, ensure_ascii=False), file=output)
            results.append(result)
            free, total = torch.cuda.mem_get_info()
            global_peak = max(global_peak, (total - free) / 2**20)
            if global_peak >= CARD_MIB - 64:
                raise RuntimeError("the CUDA card boundary approached the approved cap")
            print(json.dumps(dict(completed=len(results), card_at_boundary_mib=global_peak)), file=progress)
    if pins() != sealed["source_sha256"] or file_sha(TRAINING / "evaluation.pt") != CHECKPOINT_SHA256:
        raise ValueError("an input or the original evaluated body changed during the run")
    native.publish(record / "report.json", dict(status="COMPLETE", tag=TAG, profile_sha256=stamp,
                   answers_sha256=file_sha(record / "answers.jsonl"), checkpoint_sha256=CHECKPOINT_SHA256,
                   cases=len(results), summary=summary(results), cpu_affinity=sorted(os.sched_getaffinity(0)),
                   max_card_at_case_boundary_mib=global_peak, allocator_limit_mib=allowed / 2**20,
                   peak_tensor_mib=torch.cuda.max_memory_allocated() / 2**20,
                   elapsed_seconds=time.monotonic() - started))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--profile-sha256")
    args = parser.parse_args()
    if os.sched_getaffinity(0) != CPU_SET:
        parser.error("use exactly the approved CPU mask 0–7")
    if args.action == "prepare":
        return make_profile()
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or args.stop_by is None or args.stop_by.tzinfo is None
            or args.stop_by > AUTHORIZED_END or args.profile_sha256 is None):
        parser.error("select the one assigned device and the sealed profile with an approved stop time")
    with patch.object(native, "CARD_LIMIT_MIB", CARD_MIB):
        return supervisor.supervise(worker, PROFILE, args.profile_sha256, EVIDENCE / TAG, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
