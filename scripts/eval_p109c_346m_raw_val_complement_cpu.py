"""Score the unmeasured P109C candidate windows and join the frozen VAL panel."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import torch

from scripts import eval_p109c_346m_fixed32_raw_val_cpu as fixed


END = datetime.fromisoformat("2026-11-26T15:00:00+09:00")
PREVIOUS_SHA256 = "2EDCF6C780B233A05A411DA9D7DA0E1DEFC60F20526FD74AF67D67DB3FE59608"
OUT = fixed.EVIDENCE / "p109c_346m_r1thenr2_raw_val_joined_cpu_20261126"


def join_groups(previous, remainder):
    if previous.keys() != remainder.keys():
        raise ValueError("the lexical group identities differ")
    combined = {}
    for name, first in previous.items():
        second = remainder[name]
        count = first["targets"] + second["targets"]
        loss_sum = sum(part["targets"] * part["nll"] for part in (first, second) if part["targets"])
        combined[name] = dict(targets=count, argmax_hits=first["argmax_hits"] + second["argmax_hits"],
                              nll=loss_sum / count if count else None)
    return combined


def remaining_frames(scorer, profile, previous):
    index = scorer.pair.load_index(Path(profile["index_profile"]), profile["index_sha256"])
    frames = scorer.validation(index)
    if (len(frames) != 32 or any(tokens.shape[0] != 4 for tokens, _ in frames)
            or scorer.frame_sha(frames) != profile["frame_sha256"]):
        raise ValueError("the complete frozen VAL panel differs")
    selection = tuple(range(0, len(frames), 4))
    subset = tuple(frames[index] for index in selection)
    old = previous["binding"]
    groups = previous["groups"]
    if (old["precision"] != "CPU_FP32_MATH" or old["full_profile_sha256"] != fixed.PROFILE_SHA
            or old["scoring_source_sha256"] != profile["source_sha256"]
            or old["selection_batches"] != list(selection) or old["windows"] != 32
            or old["frame_sha256"] != scorer.frame_sha(subset) or old["targets"] != groups["all_valid"]["targets"]
            or previous["torch_threads"] != 3 or previous["cpu_affinity"] != sorted(os.sched_getaffinity(0))):
        raise ValueError("the prior scoring binds a different subset, source or CPU configuration")
    indices = tuple(index for index in range(len(frames)) if index not in selection)
    part_profile = dict(profile, validation_targets=profile["validation_targets"] - old["targets"],
                        group_targets={name: count - groups[name]["targets"]
                                       for name, count in profile["group_targets"].items()})
    return tuple(frames[index] for index in indices), indices, part_profile


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or os.sched_getaffinity(0) != set(range(8, 15))
            or args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END):
        parser.error("use the previous CPU 8–14 affinity, hide CUDA and provide a November 26 cutoff")
    cutoff = args.stop_by.timestamp()

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the remaining VAL windows reached the approved cutoff")

    raw = fixed.raw
    native, scorer = raw.v2.native, raw.val
    profile = json.loads(native.manifest_bytes(fixed.PROFILE, fixed.PROFILE_SHA))
    if profile["source_sha256"] != raw.v1.core6.digest(Path(scorer.__file__)):
        raise ValueError("the frozen scorer differs")
    previous = json.loads(native.manifest_bytes(fixed.RECORD / "candidate.json", PREVIOUS_SHA256))
    frames, indices, part_profile = remaining_frames(scorer, profile, previous)
    with patch.object(native, "STEPS", 2942):
        checkpoint, model_sha = raw.v2.completed_v2(fixed.CANDIDATE, fixed.MANIFEST_SHA)
    if previous["model_sha256"] != model_sha:
        raise ValueError("the earlier 32 windows belong to different weights")
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    check()
    OUT.mkdir(exist_ok=False)
    started = time.monotonic()
    model = raw.v1.load_model(checkpoint, 2942, "cpu")
    route = model.visit_schedule()
    with (patch.object(model.cfg, "infer_repeat", 1.), patch.object(scorer.first, "examples", return_value=())):
        if model.visit_schedule() != route:
            raise ValueError("document visibility changed the inference route")
        remainder = scorer.score_model(model, frames, part_profile, None, check)["groups"]
    if raw.v1.core6.digest(checkpoint) != model_sha:
        raise ValueError("the weight bytes changed during scoring")
    check()
    seconds = time.monotonic() - started
    combined = join_groups(previous["groups"], remainder)
    expected = dict(profile["group_targets"], all_valid=profile["validation_targets"])
    if {name: group["targets"] for name, group in combined.items()} != expected:
        raise ValueError("the two scored segments do not reproduce the frozen denominators")
    tag = raw.v1.read_json(fixed.CANDIDATE / "report.json")["tag"]
    arm = dict(model_sha256=model_sha, steps=2942, groups=combined, seconds=previous["seconds"] + seconds)
    native.publish(OUT / "report.json", dict(status="SAME_DOCUMENT_VAL_COMPLETE", precision="CPU_FP32_MATH",
                   window_sha256=profile["frame_sha256"], profile_sha256=fixed.PROFILE_SHA,
                   scoring_source_sha256=profile["source_sha256"], arms={tag: arm},
                   reused=dict(sha256=PREVIOUS_SHA256, batches=previous["binding"]["selection_batches"],
                               targets=previous["binding"]["targets"], seconds=previous["seconds"]),
                   remainder=dict(batches=indices, frame_sha256=scorer.frame_sha(frames), groups=remainder,
                                  seconds=seconds)))
    print("P109C_RAW_VAL_JOINED", tag, combined["all_valid"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
