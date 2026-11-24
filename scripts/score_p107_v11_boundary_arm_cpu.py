"""Score a sealed P107 arm while its matched arm is still training."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time

import torch

from scripts import eval_p107_v11_causal_groups_cpu as causal
from scripts import eval_p107_v11_rare_targets_cpu as rare


def score(args):
    pair = causal.pair
    original, source = rare.exact_inputs(args.profile.absolute(), args.profile_sha256)
    cohort = json.loads(pair.supervisor.manifest_bytes(args.cohort.absolute(), args.cohort_sha256))
    if (cohort["val_sha256"] != source.corpus_sha256 or cohort["index_sha256"] != original["index_sha256"]
            or cohort["scoring_source_sha256"] != pair.evaluation.core6.digest(Path(rare.__file__))):
        raise ValueError("the frozen target panel differs")
    proof_path = pair.evaluation.regular_file(args.arm_receipt.absolute())
    arm = pair.evaluation.read_json(proof_path)
    if (arm["arm"] not in pair.ARMS or arm["end"] < 512 or proof_path.parent.name != arm["arm"]
            or proof_path.name != f"receipt_{arm['end']}.json"
            or Path(arm["final"]["path"]).parent != proof_path.parent):
        raise ValueError("a sealed native arm receipt is required")
    cutoff = args.stop_by.timestamp()

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the CPU boundary scoring time ended")

    check()
    index = pair.load_index(Path(original["index_profile"]), original["index_sha256"])
    frames = causal.validation(index)
    if causal.frame_sha(frames) != original["frame_sha256"]:
        raise ValueError("the frozen natural windows differ")
    torch.set_num_threads(3)
    started = time.monotonic()
    model = causal.checkpoint_model(arm, arm["end"])
    tokenizer = pair.evaluation.load_tokenizer()
    args.record.mkdir(parents=True, exist_ok=False)
    lineage = dict(status="COMPLETE", arm=arm["arm"], steps=arm["end"], precision="CPU_FP32_MATH",
                   checkpoint_sha256=arm["final"]["sha256"], initial_sha256=arm["initial_sha256"],
                   source_end_rng=arm["source_end_rng"], causal_targets=arm["causal_targets"],
                   arm_receipt_sha256=pair.evaluation.core6.digest(proof_path),
                   score_profile_sha256=args.profile_sha256.upper(), cohort_sha256=args.cohort_sha256.upper(),
                   execution_source_sha256=pair.evaluation.core6.digest(Path(__file__)))
    results = causal.score_model(model, frames, original, tokenizer, check)
    pair.supervisor.publish(args.record / "natural.json", dict(lineage, **results, seconds=time.monotonic()-started))
    print("P107_CPU_NATURAL_ARM_COMPLETE", arm["arm"], arm["end"], results["groups"]["all_valid"], flush=True)
    started = time.monotonic()
    results = rare.score_model(model, cohort["groups"], source, cutoff)
    pair.supervisor.publish(args.record / "targeted.json", dict(lineage, rows=results, seconds=time.monotonic()-started))
    print("P107_CPU_TARGETED_ARM_COMPLETE", arm["arm"], arm["end"], {k: len(v) for k, v in results.items()}, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--cohort-sha256", required=True)
    parser.add_argument("--arm-receipt", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.record.exists():
        parser.error("CPU-only device, fresh output and an explicit cutoff timezone are required")
    score(args)


if __name__ == "__main__":
    main()
