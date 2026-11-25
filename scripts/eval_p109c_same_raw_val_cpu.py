"""Read the two completed P109C models on identical document-isolated VAL windows."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import torch

from scripts import eval_p107_v11_causal_groups_cpu as val
from scripts import eval_p109c_completed as v1
from scripts import eval_p109c_mixed_v2 as v2


def matching_readback_arm(readback, name, profile, profile_sha256, new_step, new_sha):
    try:
        arm = readback["arms"][name]
    except KeyError as error:
        raise ValueError(f"the sealed raw VAL report has no arm {name!r}") from error
    if (readback["status"] != "SAME_DOCUMENT_VAL_COMPLETE" or readback["precision"] != "CPU_FP32_MATH"
            or readback["window_sha256"] != profile["frame_sha256"] or arm["steps"] != new_step
            or readback["profile_sha256"] != profile_sha256.upper()
            or readback["scoring_source_sha256"] != profile["source_sha256"]
            or arm["model_sha256"] == new_sha):
        raise ValueError("the prior reference arm does not match the candidate's fixed VAL")
    return arm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("v2-record", "profile", "record"):
        parser.add_argument("--" + key, required=True, type=Path)
    for key in ("v2-manifest-sha256", "profile-sha256"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--v1-record", type=Path)
    parser.add_argument("--v1-manifest-sha256")
    parser.add_argument("--uniform-readback", type=Path)
    parser.add_argument("--uniform-readback-sha256")
    parser.add_argument("--uniform-readback-arm", help="Named arm in a sealed prior raw VAL report. Defaults to v2.")
    parser.add_argument("--wait-pid", type=int)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None:
        parser.error("CPU-only device mask and a timezone-aware cutoff are required")
    if bool(args.uniform_readback) != bool(args.uniform_readback_sha256):
        parser.error("provide an exact prior readback path and digest together")
    if args.uniform_readback_arm and not args.uniform_readback:
        parser.error("--uniform-readback-arm requires a sealed prior readback")
    if not args.uniform_readback and not (args.v1_record and args.v1_manifest_sha256):
        parser.error("provide the original v1 receipt or reuse a sealed uniform readback")
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    cutoff = args.stop_by.timestamp()

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the matched VAL readback reached its authorized cutoff")

    check()
    newer = args.v2_record.absolute()
    if args.wait_pid is not None:
        if args.wait_pid <= 0:
            parser.error("the training worker PID must be positive")
        v1.wait_for_training(newer, args.wait_pid, cutoff)
    native = v2.native
    profile = json.loads(native.manifest_bytes(args.profile.absolute(), args.profile_sha256))
    if v1.core6.digest(Path(val.__file__)) != profile["source_sha256"]:
        raise ValueError("the frozen natural-window scoring source changed")
    index = val.pair.load_index(Path(profile["index_profile"]), profile["index_sha256"])
    frames = val.validation(index)
    if val.frame_sha(frames) != profile["frame_sha256"]:
        raise ValueError("the matched validation window identities differ")
    new_step = v1.read_json(newer / "input.json")["steps"]
    with patch.object(native, "STEPS", new_step):
        new_model = v2.completed_v2(newer, args.v2_manifest_sha256)
    summary = {}
    prior_arm = None
    if args.uniform_readback is None:
        old_step = native.STEPS
        old_model = v1.completed_checkpoint(args.v1_record.absolute(), args.v1_manifest_sha256)
        arms = (("v1", old_step, old_model), ("v2", new_step, new_model))
    else:
        readback = json.loads(native.manifest_bytes(args.uniform_readback.absolute(), args.uniform_readback_sha256))
        prior_arm = args.uniform_readback_arm or "v2"
        uniform = matching_readback_arm(readback, prior_arm, profile, args.profile_sha256, new_step, new_model[1])
        measured = uniform["seconds"]
        if time.time() + measured + max(30, measured * .05) > cutoff:
            raise TimeoutError("the remaining window cannot fit one measured raw likelihood arm")
        summary["uniform"] = uniform
        training_tag = v1.read_json(v1.regular_file(newer / "report.json"))["tag"]
        name = "balanced_visits" if "_visit_count_" in training_tag else training_tag
        arms = ((name, new_step, new_model),)
    args.record.mkdir(exist_ok=False)
    for name, step, (path, checksum) in arms:
        check()
        started = time.monotonic()
        model = v1.load_model(path, step, "cpu")
        inference_route = model.visit_schedule()
        with (patch.object(model.cfg, "infer_repeat", 1.),
              patch.object(val.first, "examples", return_value=())):
            if model.visit_schedule() != inference_route:
                raise ValueError("document visibility must preserve the original inference visit order")
            groups = val.score_model(model, frames, profile, None, check)["groups"]
        del model
        if v1.core6.digest(path) != checksum:
            raise ValueError("the evaluation weight bytes changed during scoring")
        summary[name] = dict(model_sha256=checksum, steps=step, groups=groups,
                             seconds=time.monotonic()-started)
        native.publish(args.record / f"{name}.json", summary[name])
        print("P109C_RAW_VAL_ARM_COMPLETE", name, groups["all_valid"], flush=True)
    native.publish(args.record / "report.json", dict(status="SAME_DOCUMENT_VAL_COMPLETE",
                   precision="CPU_FP32_MATH", window_sha256=profile["frame_sha256"],
                   profile_sha256=args.profile_sha256.upper(),
                   scoring_source_sha256=profile["source_sha256"], arms=summary,
                   prior_readback_sha256=args.uniform_readback_sha256, prior_readback_arm=prior_arm))


if __name__ == "__main__":
    main()
