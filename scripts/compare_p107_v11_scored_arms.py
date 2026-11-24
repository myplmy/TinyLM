"""Compare frozen P107 CPU readbacks without scoring either model again."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np


CONTROLS = ("steps", "precision", "initial_sha256", "source_end_rng", "causal_targets",
            "score_profile_sha256", "cohort_sha256", "execution_source_sha256")
IDENTITY = ("document", "prefix_start", "target", "token")
BOOTSTRAPS = 10000


def read_arm(path, policy):
    records = {}
    hashes = {}
    for name in ("natural", "targeted"):
        content = (path / f"{name}.json").read_bytes()
        hashes[name] = sha256(content).hexdigest().upper()
        row = json.loads(content)
        if row["status"] != "COMPLETE" or row["arm"] != policy:
            raise ValueError("both frozen evaluation panels must be complete for the named arm")
        records[name] = row
    keys = (*CONTROLS, "checkpoint_sha256", "arm_receipt_sha256")
    if any(records["natural"][key] != records["targeted"][key] for key in keys):
        raise ValueError("the natural and targeted panels used different arm receipts")
    return records, hashes


def bootstrap_targets(before, after, rng):
    old_keys = [tuple(row[key] for key in IDENTITY) for row in before]
    new_keys = [tuple(row[key] for key in IDENTITY) for row in after]
    if old_keys != new_keys or len(set(old_keys)) != len(old_keys):
        raise ValueError("the targeted panels do not have the same unique positions")
    if not before:
        return dict(targets=0, documents=0)
    docs, membership = np.unique([key[0] for key in old_keys], return_inverse=True)
    delta = np.asarray([b["nll"] - a["nll"] for a, b in zip(before, after, strict=True)])
    if not np.isfinite(delta).all():
        raise ValueError("nonfinite token likelihood in a complete panel")
    interval = None
    if len(docs) > 1:
        sums = np.bincount(membership, weights=delta)
        counts = np.bincount(membership)
        draws = rng.integers(0, len(docs), size=(BOOTSTRAPS, len(docs)))
        interval = np.percentile(sums[draws].sum(1) / counts[draws].sum(1), (2.5, 97.5)).tolist()
    return dict(targets=len(before), documents=len(docs), nll_delta_adaptive_minus_observe=float(delta.mean()),
                nll_delta_document_bootstrap_95=interval,
                old_nll=float(np.mean([row["nll"] for row in before])),
                new_nll=float(np.mean([row["nll"] for row in after])),
                old_median_rank=float(np.median([row["rank"] for row in before])),
                new_median_rank=float(np.median([row["rank"] for row in after])),
                top1_gains=sum(not a["top1"] and b["top1"] for a, b in zip(before, after, strict=True)),
                top1_losses=sum(a["top1"] and not b["top1"] for a, b in zip(before, after, strict=True)))


def compare(observe, adaptive):
    a, ah = read_arm(observe, "observe")
    b, bh = read_arm(adaptive, "adaptive")
    before, after = a["natural"], b["natural"]
    if any(before[key] != after[key] for key in CONTROLS):
        raise ValueError("the two arms do not have a matched boundary and evaluation contract")
    if before["groups"].keys() != after["groups"].keys() or a["targeted"]["rows"].keys() != b["targeted"]["rows"].keys():
        raise ValueError("the two panels must have identical group definitions")
    natural = {}
    for name, old in before["groups"].items():
        new = after["groups"][name]
        if old["targets"] != new["targets"]:
            raise ValueError("different natural target counts")
        natural[name] = dict(targets=old["targets"], old_nll=old["nll"], new_nll=new["nll"],
                             nll_delta_adaptive_minus_observe=new["nll"] - old["nll"] if old["targets"] else None,
                             old_top1=old["argmax_hits"], new_top1=new["argmax_hits"])
    rng = np.random.default_rng(1337)
    targeted = {key: bootstrap_targets(rows, b["targeted"]["rows"][key], rng)
                for key, rows in a["targeted"]["rows"].items()}
    pairs = list(zip(before["first_use"], after["first_use"], strict=True))
    if any((x["case"], x["language"], x["expected"]) != (y["case"], y["language"], y["expected"])
           for x, y in pairs):
        raise ValueError("the two first-use prompt sets differ")
    return dict(status="MATCHED_READBACK", steps=before["steps"], inputs={"observe": ah, "adaptive": bh},
                natural=natural, targeted=targeted, bootstrap_draws=BOOTSTRAPS,
                first_use=dict(rows=len(pairs), exact=[sum(row["exact"] for row in branch["first_use"])
                                                      for branch in (before, after)],
                               answer_and_end=[sum(row["exact"] and row["ended"] for row in branch["first_use"])
                                               for branch in (before, after)]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observe", type=Path, required=True)
    parser.add_argument("--adaptive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.observe, args.adaptive)
    with args.output.open("x", encoding="utf-8") as output:
        print(json.dumps(result, indent=2, allow_nan=False), file=output)
    print(result["status"], result["steps"], result["natural"]["all_valid"], result["first_use"])


if __name__ == "__main__":
    main()
