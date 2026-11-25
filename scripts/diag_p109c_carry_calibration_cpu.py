"""Fit single decision boundaries on separate roots and reuse the fixed DEV logits."""

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
import json
import math
import os
from pathlib import Path
from time import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_carry_evidence_cpu as prior


REF = prior.REF
TAG = "p109c_carry_calibration_cpu_20261126"
PROFILE = REF.EVIDENCE / f"{TAG}_profile.json"
OUT = REF.EVIDENCE / TAG
END = datetime.fromisoformat("2026-11-26T14:00:00+09:00")
CALIBRATE = ("operands", "digits", "true_sum")
PER_GROUP = 16


def prepare():
    source_path = prior.prior.OUT / "inputs.json"
    source = REF.completed.read_json(source_path)
    original, tokenizer = prior.prepare()
    before_path = prior.OUT / "report.json"
    before = REF.completed.read_json(before_path)
    source_sha = REF.file_sha(prior.PROFILE)
    if (before["status"] != "COMPLETE" or before["profile_sha256"] != source_sha
            or original != REF.completed.read_json(prior.PROFILE)
            or before["summary"]["all"]["true_sum"]["first_token"] != 16):
        raise ValueError("the saved diagnosis must bind the same inputs and the unchanged default boundary")
    train = []
    for language in ("ko", "en"):
        for gold in (0, 1):
            eligible = [case for case in source["training_cases"] if case["language"] == language and case["carry"] == gold]
            selected = sorted(eligible, key=lambda case: case["id"])[:PER_GROUP]
            if len(selected) != PER_GROUP:
                raise ValueError("balance the two labels in both training languages")
            train.extend(selected)
    train_ids = {case["id"] for case in train}
    dev_ids = {case["id"] for case in original["cases"]}
    if len(train_ids) != 4*PER_GROUP or train_ids & dev_ids:
        raise ValueError("calibration roots must be distinct from the fixed DEV facts")
    return dict(training_roots=sorted(train_ids), training_sha256=REF.file_sha(source_path),
                development_report_sha256=REF.file_sha(before_path), development_profile_sha256=source_sha,
                source_sha256=REF.file_sha(Path(__file__)), parent_sha256=REF.CHECKPOINT_SHA256,
                modes=list(CALIBRATE), position="first response token before EOT"), tokenizer, train, before["rows"]


def training_scores(model, tokenizer, cases, cutoff):
    data = defaultdict(list)
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case in cases:
            for arm in CALIBRATE:
                if time() >= cutoff:
                    raise TimeoutError("the score calibration reached its CPU cutoff")
                prompt = prior.request(case, arm)
                ids = tokenizer.encode(prompt).ids
                labels = [tokenizer.encode(prompt + label).ids for label in ("0", "1")]
                if any(item[:-1] != ids for item in labels) or labels[0][-1] == labels[1][-1]:
                    raise ValueError("both carry labels must extend the same prefix by one token")
                hidden = model(torch.tensor([ids], dtype=torch.long), return_hidden=True)[:, -1]
                logp = model._head_logits(hidden).float()[0].log_softmax(-1)
                score = float(logp[labels[1][-1]] - logp[labels[0][-1]])
                if not math.isfinite(score):
                    raise ValueError("the frozen logits must be finite")
                data[case["language"], arm].append(dict(id=case["id"], gold=case["carry"], margin=score))
    return data


def fit(rows):
    ordered = sorted({row["margin"] for row in rows})
    limits = [0., ordered[0] - 1., ordered[-1] + 1.]
    limits.extend((a + b)/2. for a, b in zip(ordered, ordered[1:]))

    def errors(bound):
        misses = sum(int(row["margin"] > bound) != row["gold"] for row in rows)
        return misses, abs(bound), bound

    threshold = min(limits, key=errors)
    return dict(threshold=threshold, correct=len(rows) - errors(threshold)[0], count=len(rows))


def score(rows, boundaries):
    evidence = []
    for row in rows:
        source_arm = "true_sum" if row["arm"] == "wrong_sum" else row["arm"]
        threshold = boundaries[row["language"], source_arm]["threshold"]
        margin = row["choice_logp"][1] - row["choice_logp"][0]
        evidence.append(dict(id=row["id"], language=row["language"], mode=row["arm"], gold=row["gold"],
                             threshold=threshold, margin=margin, default=row["choice_prediction"],
                             calibrated=int(margin > threshold)))
    results = {}
    for language in ("ko", "en", "all"):
        collection = [row for row in evidence if language in (row["language"], "all")]
        results[language] = {}
        for mode in prior.ARMS:
            group = [row for row in collection if row["mode"] == mode]
            results[language][mode] = dict(count=len(group), default=sum(row["default"] == row["gold"] for row in group),
                calibrated=sum(row["calibrated"] == row["gold"] for row in group))
    return dict(summary=results, rows=evidence)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("the independent threshold diagnosis uses CPU 14 only")
    if args.mode == "prepare":
        if args.profile_sha256 or args.stop_by or PROFILE.exists() or OUT.exists():
            parser.error("prepare needs a new model-free profile")
        profile, *_ = prepare()
        REF.native.publish(PROFILE, profile)
        print(PROFILE, REF.file_sha(PROFILE), flush=True)
        return
    if (not args.profile_sha256 or args.stop_by is None or args.stop_by.tzinfo is None
            or not datetime.now().astimezone() < args.stop_by <= END or OUT.exists()):
        parser.error("the fixed profile and a future cutoff are required")
    profile, tokenizer, train, dev = prepare()
    if profile != json.loads(REF.native.manifest_bytes(PROFILE, args.profile_sha256)):
        raise ValueError("the bound training and development panels changed")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    checkpoint = REF.checkpoint()
    model = REF.completed.load_model(checkpoint, 2942, "cpu")
    if len(model.visit_schedule()) != 28:
        raise ValueError("calibration requires the same frozen native R2 as development")
    OUT.mkdir(exist_ok=False)
    stored = training_scores(model, tokenizer, train, args.stop_by.timestamp())
    boundaries = {key: fit(rows) for key, rows in stored.items()}
    scored = score(dev, boundaries)
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", profile_sha256=args.profile_sha256.upper(),
        threshold_training={"/".join(key): dict(boundaries[key], rows=rows) for key, rows in stored.items()}, **scored))
    if REF.file_sha(checkpoint) != profile["parent_sha256"]:
        raise ValueError("the frozen evaluation checkpoint changed")
    print("P109C_CARRY_CALIBRATION", json.dumps(scored["summary"]), flush=True)


if __name__ == "__main__":
    main()
