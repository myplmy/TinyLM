"""Fit a fresh three-row edit to actual development errors and verify new tables."""

import argparse
from datetime import datetime
from itertools import chain
import os
from pathlib import Path
from random import Random
import time

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_broad_guard_projection_cpu as broad


joint, previous = broad.joint, broad.previous
author = previous.composition.AUTHOR
CROSSED = previous.OUT.with_name("p108_crossed_guard_projection_cpu_v1_20261123") / "report.json"
SEED = {"development": 418127, "independent": 902327}
SHOTS = {"development": 18, "independent": 24}


def requests(tokenizer, split):
    rng = Random(SEED[split])
    records = {}
    for language in ("ko", "en"):
        for index in range(SHOTS[split]):
            prefixes = rng.sample(range(16, 97), 2)
            numbers = (prefixes[0] * 100 + 31, prefixes[1] * 100 + 71, 1000, rng.randrange(1001, 1290))
            assigned = tuple(rng.sample(numbers, len(numbers)))
            table = author.values_text(language, assigned, rng.sample(range(4), 4))
            root = author.digest(["table", assigned])
            if root in records:
                raise ValueError("a newly generated table was repeated")
            order = (index % 3, (index + 1) % 3)
            for kind in ("single", "correction"):
                target = numbers[order[0 if kind == "correction" else 1]]
                field = assigned.index(target)
                if split == "development":
                    question = author.field_question(language, field, 1)
                else:
                    field_name = author.FIELDS[language][field]
                    question = (f"장부에서 {field_name} 줄을 찾아 숫자를 하나만 써 주세요." if language == "ko"
                                else f"Find the {field_name} entry in this list and return its number alone.")
                turns = [("user", table + " " + question)]
                if kind == "correction":
                    turns.extend((("assistant", str(numbers[3])), ("user", question)))
                result = author.row(root, "guarded_table_repair", language,
                                    [*turns, ("assistant", str(target))], view=kind)["record"]
                wire = previous.prior.foundation.data
                encoded = wire.encode_record(result, tokenizer, context=previous.trial.WIDTH)
                prompt = wire.generation_prompt(tokenizer, result)
                records.setdefault(root, dict(language=language))[kind] = (encoded, prompt, str(target))
    return records


def constraint_data(model, tokens, anchor, development, guard, cutoff):
    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the allowed CPU output-edit experiment has ended")

    certified = []
    uneditable = []
    extra = []
    for root, group in development.items():
        for view in ("single", "correction"):
            encoded, _, _ = group[view]
            check()
            keys, scores, labels = joint.projected(model, encoded)
            scores[:, tokens] += keys @ anchor.double().T
            mismatch = torch.nonzero(scores.argmax(1).ne(labels)).flatten()
            if not len(mismatch):
                extra.append(("development_correct", keys, scores, labels))
                continue
            if view == "single":
                continue
            index = int(mismatch[0])
            rows, bounds, fixed = joint.constraint_rows(keys, scores, labels, tokens, "fit")
            info = dict(root=root, language=group["language"], first_error=index, gold=int(labels[index]),
                        rival=int(scores[index].argmax()), immutable_violations=fixed)
            if fixed or not rows:
                uneditable.append(info)
                continue
            direction, _, error = joint.project(np.zeros_like(anchor.numpy()), rows,
                                                np.asarray(bounds) - broad.ROUNDING_SLACK, check)
            certified.append((float(np.linalg.norm(direction)), error, info, rows, bounds))

    hard, hard_bounds, info = broad.guard_pool(model, guard, tokens, anchor, check)
    for _, keys, scores, labels in extra:
        rows, bounds, fixed = joint.constraint_rows(keys, scores, labels, tokens, "protect")
        if fixed:
            raise ValueError("a currently correct immutable token failed its own protection")
        hard.extend(rows)
        hard_bounds.extend(bounds)
    return certified, uneditable, hard, hard_bounds, info


def choose(anchor, ready, hard, hard_limits, budget, check):
    targets, limits, chosen, trials = [], [], [], []
    realized, solution = anchor, np.zeros_like(anchor.numpy())
    usable = [item for item in ready if item[0] <= budget and item[1] <= 1e-7]
    for unguarded_norm, _, item, new_rows, new_limits in sorted(usable, key=lambda row: (row[0], row[2]["root"]))[:12]:
        check()
        rows = [*hard, *targets, *new_rows]
        bounds = np.asarray([*hard_limits, *limits, *new_limits])
        update, cycles, solver_violation = joint.project(solution, rows, bounds - broad.ROUNDING_SLACK, check)
        trial = (anchor.double() + torch.from_numpy(update)).half().float()
        change = (trial - anchor).double().numpy().ravel()
        max_violation = float(np.max(np.stack(rows) @ change - bounds))
        norm = float(np.linalg.norm(change))
        fits = max_violation <= 0 and 0 < norm <= budget
        trials.append(dict(item, accepted=fits, unguarded_proposal_l2=unguarded_norm, fp16_l2=norm,
                           fp16_max_violation=max_violation, solver_violation=solver_violation, cycles=cycles))
        if fits:
            targets.extend(new_rows)
            limits.extend(new_limits)
            chosen.append(item["root"])
            realized, solution = trial, update
    return realized, chosen, trials


def measure(model, tokens, delta, tokenizer, items, check):
    for_id = [(root, view, group[view][1], group[view][2])
              for root, group in items.items() for view in ("single", "correction")]
    with joint.output_patch(model, tokens, delta):
        measured = joint.record_outputs(model, tokenizer, for_id, check)
    for row, (_, _, prompt, _) in zip(measured, for_id, strict=True):
        row["prompt_sha256"] = author.digest(prompt)
    return measured


def summarize(before, after):
    result = dict(before=sum(row["correct"] for row in before), after=sum(row["correct"] for row in after))
    for left, right in zip(before, after, strict=True):
        if any(left[key] != right[key] for key in ("root", "view", "target", "prompt_sha256")):
            raise ValueError("the paired generation changed its frozen input")
    result["gained"] = sum(not a["correct"] and b["correct"] for a, b in zip(before, after, strict=True))
    result["lost"] = sum(a["correct"] and not b["correct"] for a, b in zip(before, after, strict=True))
    result["protected_sequence_changes"] = sum(a["correct"] and a["ids"] != b["ids"]
                                               for a, b in zip(before, after, strict=True))
    return result


def run(record, cutoff):
    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the allowed CPU output-edit experiment has ended")

    check()
    anchor_path = previous.OUT / "trained_overlay.pt"
    base = previous.solver.first.CHECKPOINT
    paths = (base, anchor_path, CROSSED)
    pins = dict((str(path), previous.trial.file_sha(path)) for path in paths)
    reference = previous.trial.read_json(CROSSED)
    if (reference["status"] != "REGRESSION_READBACK_COMPLETE"
            or reference["base_checkpoint_sha256"] != pins[str(base)]
            or reference["baseline_overlay_sha256"] != pins[str(anchor_path)]):
        raise ValueError("the prior realized budget requires the same anchor")
    tokenizer, _, cases, _, _ = previous.trial.load_cases()
    development, independent = (requests(tokenizer, name) for name in SEED)
    old = set(chain.from_iterable(cases.values()))
    if old & (development.keys() | independent.keys()) or development.keys() & independent.keys():
        raise ValueError("original, development and independent table roots must be disjoint")
    saved = torch.load(base, weights_only=True, map_location="cpu")
    sidecar = torch.load(anchor_path, weights_only=True, map_location="cpu")
    model = previous.prior.TiedMLPTransformer(previous.prior.TMTConfig(**saved["config"])).eval().requires_grad_(False)
    model.load_state_dict(saved["model"], strict=True)
    if previous.trial.state_sha(model.state_dict()) != sidecar["body_sha256"]:
        raise ValueError("the original edit is bound to another body")
    model.freeze_quant()
    tokens, anchor = torch.tensor(sidecar["ids"], dtype=torch.long), sidecar["delta"].float()
    budget = reference["candidate_l2"]
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        ready, uneditable, hard, hard_limits, guard = constraint_data(
            model, tokens, anchor, development, cases["validation"], cutoff)
        delta, chosen, trials = choose(anchor, ready, hard, hard_limits, budget, check)
        print("P108_NEW_DIRECTION_FIXED", len(ready), len(uneditable), len(chosen), flush=True)
        outcome = {}
        for name, cohort in (("development", development), ("independent", independent)):
            before = measure(model, tokens, anchor, tokenizer, cohort, check)
            after = measure(model, tokens, delta, tokenizer, cohort, check) if chosen else before
            outcome[name] = dict(rows=len(after), metrics=summarize(before, after), before=before, after=after)
    if pins != {str(path): previous.trial.file_sha(path) for path in paths}:
        raise ValueError("a frozen input changed")
    record.mkdir(exist_ok=False)
    joint.publish.publish(record / "report.json", dict(
        status="NEW_GUARDED_DIRECTION_READBACK_COMPLETE", tag=record.name, source_sha256=previous.trial.file_sha(Path(__file__)),
        mutable_rows=tokens.tolist(), fp16_l2_cap=budget, fp16_l2=float((delta-anchor).norm()),
        chosen_development=chosen, uneditable_first_pass=uneditable, eligible_candidates=len(ready),
        candidate_baseline_mismatches=len(ready)+len(uneditable), trials=trials, original_guard=guard,
        inputs=pins, folds={name: author.digest(sorted(group)) for name, group in
                            (("development", development), ("independent", independent))}, outcomes=outcome,
        fit_contains_independent_inputs=False, body_written=False))
    print({name: item["metrics"] for name, item in outcome.items()}, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None or args.record.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("require a fresh record and authorized CPU-only cutoff")
    if args.source_sha256.upper() != previous.trial.file_sha(Path(__file__)).upper():
        parser.error("the experiment source changed after sealing")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    run(args.record, args.stop_by.timestamp())


if __name__ == "__main__":
    main()
