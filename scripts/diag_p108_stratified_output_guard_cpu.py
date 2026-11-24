"""Compare explicit protection of known correct editable tokens on fresh tables."""

import argparse
from collections import Counter
from datetime import datetime
from itertools import chain
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_new_guarded_direction_cpu as prior


joint, previous, author = prior.joint, prior.previous, prior.author
FIRST_RESULT = prior.CROSSED.parent.parent / "p108_new_guarded_direction_cpu_v1_20261123/report.json"


def additional_requests(tokenizer):
    with (patch.dict(prior.SEED, protection=573281, fresh=1449831),
          patch.dict(prior.SHOTS, protection=36, fresh=24)):
        return prior.requests(tokenizer, "protection"), prior.requests(tokenizer, "fresh")


def prepare_guard(model, ids, anchor, cases, check):
    # Use only complete development successes. Keep vulnerable answer rows from losing score.
    rows, limits = [], []
    gathered = Counter()
    for group in cases.values():
        for view in ("single", "correction"):
            check()
            keys, scores, wanted = joint.projected(model, group[view][0])
            scores[:, ids] += keys @ anchor.double().T
            if not torch.equal(scores.argmax(-1), wanted):
                continue
            positives, room, fixed = joint.constraint_rows(keys, scores, wanted, ids, "protect")
            if fixed:
                raise ValueError("the anchor failed a known correct immutable position")
            rows.extend(positives)
            limits.extend(room)
            gathered[(view, "correct_answers")] += 1
            for key, label in zip(keys, wanted, strict=True):
                match = torch.nonzero(ids == label).flatten()
                if not len(match):
                    continue
                normal = key.numpy()
                norm = np.linalg.norm(normal)
                if norm <= 1e-12:
                    continue
                guarded = np.zeros(tuple(anchor.shape), dtype=np.float64)
                guarded[int(match[0])] = -normal / norm
                rows.append(guarded.ravel())
                limits.append(0.)
                gathered[(view, f"editable_{int(label)}")] += 1
    return rows, limits, {f"{view}:{item}": count for (view, item), count in gathered.items()}


def run(record, cutoff):
    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the approved output guard contrast reached its cutoff")

    check()
    baseline = previous.OUT / "trained_overlay.pt"
    body = previous.solver.first.CHECKPOINT
    paths = (body, baseline, FIRST_RESULT)
    pins = {str(path): previous.trial.file_sha(path) for path in paths}
    measured = previous.trial.read_json(FIRST_RESULT)
    if (measured["source_sha256"] != previous.trial.file_sha(Path(prior.__file__))
            or any(measured["inputs"][str(path)] != pins[str(path)] for path in (body, baseline))):
        raise ValueError("the earlier proposal and its exact base must be preserved")

    tokenizer, _, cases, _, _ = previous.trial.load_cases()
    development = prior.requests(tokenizer, "development")
    old_test = prior.requests(tokenizer, "independent")
    development_guard, fresh_test = additional_requests(tokenizer)
    all_sets = [set(data) for data in (*cases.values(), development, old_test, development_guard, fresh_test)]
    if sum(map(len, all_sets)) != len(set(chain.from_iterable(all_sets))):
        raise ValueError("original, selection, protection and test root sets must be disjoint")
    if measured["folds"] != dict(development=author.digest(sorted(development)), independent=author.digest(sorted(old_test))):
        raise ValueError("the earlier proposal's author seeds changed")
    sidecar = torch.load(baseline, weights_only=True, map_location="cpu")
    saved = torch.load(body, weights_only=True, map_location="cpu")
    model = previous.prior.TiedMLPTransformer(previous.prior.TMTConfig(**saved["config"])).eval().requires_grad_(False)
    model.load_state_dict(saved["model"], strict=True)
    if previous.trial.state_sha(model.state_dict()) != sidecar["body_sha256"]:
        raise ValueError("the frozen output sidecar belongs to another body")
    model.freeze_quant()
    ids, anchor = torch.tensor(sidecar["ids"], dtype=torch.long), sidecar["delta"].float()
    budget = measured["fp16_l2_cap"]
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        ready, _, hard, room, _ = prior.constraint_data(model, ids, anchor, development, cases["validation"], cutoff)
        original, chosen, trials = prior.choose(anchor, ready, hard, room, budget, check)
        if (chosen != measured["chosen_development"]
                or abs(float((original - anchor).norm()) - measured["fp16_l2"]) > 1e-6):
            raise ValueError("the earlier development proposal could not be matched")
        guard, room_extra, summary = prepare_guard(model, ids, anchor, development_guard, check)
        protected, selected, attempts = prior.choose(anchor, ready, [*hard, *guard], [*room, *room_extra], budget, check)
        print("P108_STRATIFIED_GUARD_FIXED", len(guard), len(chosen), len(selected), flush=True)
        before = prior.measure(model, ids, anchor, tokenizer, fresh_test, check)
        earlier = prior.measure(model, ids, original, tokenizer, fresh_test, check)
        candidate = prior.measure(model, ids, protected, tokenizer, fresh_test, check) if selected else before
    if pins != {str(path): previous.trial.file_sha(path) for path in paths}:
        raise ValueError("a frozen input changed")
    metrics = dict(prior_direction=prior.summarize(before, earlier), stratified_guard=prior.summarize(before, candidate))
    record.mkdir(exist_ok=False)
    joint.publish.publish(record / "report.json", dict(status="P108_STRATIFIED_GUARD_COMPLETE",
        source_sha256=previous.trial.file_sha(Path(__file__)), input_sha256=pins, editable_ids=ids.tolist(),
        guard_roots_sha256=author.digest(sorted(development_guard)), test_roots_sha256=author.digest(sorted(fresh_test)),
        guard_counts=summary, guard_constraints=len(guard), fp16_l2_cap=budget,
        prior_direction_l2=float((original - anchor).norm()), stratified_l2=float((protected - anchor).norm()),
        prior_chosen_roots=chosen, stratified_chosen_roots=selected, prior_trials=trials, stratified_trials=attempts,
        metrics=metrics, anchor=before, prior_direction=earlier, stratified_guard=candidate, base_model_written=False))
    print(metrics, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--source-sha256", required=True)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or args.record.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or args.source_sha256.upper() != previous.trial.file_sha(Path(__file__)).upper()):
        parser.error("requires a sealed CPU-only run with an authorized cutoff")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    run(args.record, args.stop_by.timestamp())


if __name__ == "__main__":
    main()
