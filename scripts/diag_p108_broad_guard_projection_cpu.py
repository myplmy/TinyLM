"""Fit the three existing output rows with guards across the full development split."""

import argparse
from datetime import datetime
from itertools import chain
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_joint_guarded_output_cpu as joint


previous = joint.previous
OLD_REPORT = joint.OUT.with_name("p108_joint_guarded_output_cpu_fp16_slack_v2_20261123") / "report.json"
ROUNDING_SLACK = .0001


def crossed_requests(tok, split):
    existing = {tuple(ids) for row in split.values() for ids in row["prompts"].values()}
    requests = previous.composition.novel_requests(tok, split, sorted(split))
    for row in requests:
        prefix = tuple(row["ids"])
        if prefix in existing:
            continue
        existing.add(prefix)
        answer = tuple(tok.encode(row["wanted"], add_special_tokens=False).ids) + (4,)
        if len(answer) <= 1 or 4 in answer[:-1] or len(prefix) + len(answer) > previous.trial.WIDTH:
            raise ValueError("the crossed guard must retain a complete answer and its turn ending")
        yield row["family"], SimpleNamespace(x=prefix + answer[:-1], y=(-100,) * (len(prefix)-1) + answer)


def guard_pool(model, split, tokens, initial, check, extra=()):
    constraints, limits = [], []
    counts = dict(requests=0, correct_requests=0, protected_positions=0, fixed_violations=0)
    cohorts = {}
    original = (("original", row["records"][view]) for _, row in sorted(split.items()) for view in previous.prior.VIEWS)
    for family, encoded in chain(original, extra):
        check()
        keys, scores, wanted = joint.projected(model, encoded)
        cohort = cohorts.setdefault(family, dict(requests=0, protected_requests=0))
        cohort["requests"] += 1
        counts["requests"] += 1
        scores[:, tokens] += keys @ initial.double().T
        if not torch.equal(scores.argmax(1), wanted):
            continue
        cohort["protected_requests"] += 1
        counts["correct_requests"] += 1
        counts["protected_positions"] += len(wanted)
        rows, bounds, fixed = joint.constraint_rows(keys, scores, wanted, tokens, "protect")
        constraints.extend(rows)
        limits.extend(bounds)
        counts["fixed_violations"] += fixed
    if extra:
        counts["cohorts"] = cohorts
        if set(cohorts) != {"original", "same_value", "different_value"}:
            raise ValueError("the added protection must cover both crossed development families")
    return constraints, limits, counts


def run(output, cutoff, *, crossed=False):
    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the broad guard comparison reached its cutoff")

    check()
    prior_sha = previous.trial.file_sha(OLD_REPORT)
    rejected = previous.trial.read_json(OLD_REPORT)
    source = previous.OUT / "trained_overlay.pt"
    base = previous.solver.first.CHECKPOINT
    sha, overlay_sha = previous.trial.file_sha(base), previous.trial.file_sha(source)
    if sha != rejected["base_checkpoint_sha256"] or overlay_sha != rejected["old_overlay_sha256"]:
        raise ValueError("the old regression reference used different weights")
    plan, (tok, _, cases, dev, _, _) = previous.prepare()
    starting_sha = previous.trial.file_sha(previous.INITIAL)
    original = torch.load(previous.INITIAL, map_location="cpu", weights_only=True)
    accepted = torch.load(source, map_location="cpu", weights_only=True)
    data = torch.load(base, map_location="cpu", weights_only=True)
    model = previous.prior.TiedMLPTransformer(previous.prior.TMTConfig(**data["config"])).eval()
    model.load_state_dict(data["model"], strict=True)
    if (previous.trial.state_sha(model.state_dict()) != accepted["body_sha256"]
            or original["body_sha256"] != accepted["body_sha256"]
            or list(accepted["ids"]) != list(original["ids"]) or list(accepted["ids"]) != rejected["mutable_rows"]):
        raise ValueError("the existing sidecars disagree about the frozen body or changed rows")
    model.freeze_quant()
    tokens = torch.tensor(accepted["ids"], dtype=torch.long)
    initial = accepted["delta"].float()
    target = (initial - original["delta"].float()).double().numpy()
    report = dict(status="NOT_ADMITTED", prior_report_sha256=prior_sha, base_checkpoint_sha256=sha,
                  initial_overlay_sha256=starting_sha, baseline_overlay_sha256=overlay_sha,
                  mutable_rows=tokens.tolist(), rounding_slack=ROUNDING_SLACK, holdout_used_for_fitting=False)
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        development = cases["validation"]
        extra = tuple(crossed_requests(tok, development)) if crossed else ()
        constraints, limits, counts = guard_pool(model, development, tokens, initial, check, extra)
        fixed = counts["fixed_violations"]
        for root in plan["targets"]:
            keys, scores, wanted = joint.projected(model, dev[root]["records"]["correction"])
            scores[:, tokens] += keys @ initial.double().T
            rows, bounds, unavailable = joint.constraint_rows(keys, scores, wanted, tokens, "fit")
            constraints.extend(rows)
            limits.extend(bounds)
            fixed += unavailable
        if counts["protected_positions"] <= rejected["guard_positions"]:
            raise ValueError("the full development split did not add any guarded positions")
        matrix, limits = np.stack(constraints), np.asarray(limits)
        delta, iterations, residual = joint.project(target, constraints, limits-ROUNDING_SLACK, check)
        actual = (initial.double() + torch.from_numpy(delta)).half().float()
        realized = (actual - initial).double().numpy().ravel()
        maximum = float(np.max(matrix @ realized - limits))
        report.update(guard=counts, inequalities=len(limits), fixed_violations=fixed,
                      unprojected_violation=float(np.max(matrix @ target.ravel() - limits)),
                      fp64_violation=residual, fp16_violation=maximum, iterations=iterations,
                      candidate_l2=float(np.linalg.norm(realized)))
        if not fixed and maximum <= 0:
            samples = [(root, view, item["prompts"][view], item["gold"])
                       for root, item in cases["test"].items() for view in previous.prior.VIEWS]
            actual_keys = [(root, view, value) for root, view, _, value in samples]
            previous_keys = [(row["root"], row["view"], row["target"]) for row in rejected["before"]]
            if actual_keys != previous_keys:
                raise ValueError("the frozen regression questions differ from prior evidence")
            with joint.output_patch(model, tokens, actual):
                after = joint.record_outputs(model, tok, samples, check)
            before = rejected["before"]
            pairs = list(zip(before, after, strict=True))
            report.update(status="REGRESSION_READBACK_COMPLETE", after=after,
                          baseline_correct=sum(row["correct"] for row in before),
                          candidate_correct=sum(row["correct"] for row in after),
                          changed_protected=sum(a["correct"] and a["ids"] != b["ids"] for a, b in pairs),
                          gained=sum(not a["correct"] and b["correct"] for a, b in pairs),
                          lost=sum(a["correct"] and not b["correct"] for a, b in pairs))
    if tuple(map(previous.trial.file_sha, (base, source, previous.INITIAL, OLD_REPORT))) != (sha, overlay_sha, starting_sha, prior_sha):
        raise ValueError("the existing base, sidecars or regression receipt changed")
    output.mkdir(exist_ok=False)
    joint.publish.publish(output / "report.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "after"}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--crossed-guards", action="store_true")
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.record.exists():
        parser.error("a fresh CPU-only record and authorized cutoff are required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    run(args.record, args.stop_by.timestamp(), crossed=args.crossed_guards)


if __name__ == "__main__":
    main()
