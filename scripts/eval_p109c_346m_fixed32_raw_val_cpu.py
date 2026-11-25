"""Score a fixed subset of the sealed P109C VAL when the whole pass cannot fit."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import eval_p109c_same_raw_val_cpu as raw


END = datetime.fromisoformat("2026-11-25T15:00:00+09:00")
EVIDENCE = Path(__file__).resolve().parents[1] / "test_result" / "evidence"
PROFILE = EVIDENCE.parent.parent / "data_cache/p107_v11_causal_group_profile_v1_20261121.json"
PROFILE_SHA = "D1AD853B24215DA37AF5588FC21627C92B643DA169E5833BDD34BBB71E2A9028"
MANIFEST_SHA = "1C21062F31EA807B35E2F623AE6544094F216F49EED1BBE75F61E1A66EECC1D7"
ARCHIVE_TAG = "p109c_integrated_scratch_v3_v11_chat32_s1337"
ARCHIVE_RECORD = EVIDENCE / f"{ARCHIVE_TAG}_run1_20261124"
ARCHIVE_VAL = EVIDENCE / "p109c_integrated_scratch_v3_same_raw_val_cpu_v1_20261124/report.json"
ARCHIVE_VAL_SHA = "718967DA7EDB511EB671C286E8C517DF7E6B0D6358E67B4F28C2A3BE1C97B21F"
CANDIDATE = EVIDENCE / "p109c_346m_r1thenr2_20261125_chat32_run1"
RECORD = EVIDENCE / "p109c_346m_fixed32_raw_val_cpu_20261125_run1"


def fixed_frames(profile):
    scorer = raw.val
    index = scorer.pair.load_index(Path(profile["index_profile"]), profile["index_sha256"])
    frames = scorer.validation(index)
    if len(frames) != 32 or any(tokens.shape[0] != 4 for tokens, _ in frames):
        raise ValueError("the frozen panel is expected to contain 32 batches of four windows")
    if scorer.frame_sha(frames) != profile["frame_sha256"]:
        raise ValueError("the frozen full VAL frames differ")
    selected = tuple(range(0, len(frames), 4))
    subset = tuple(frames[index] for index in selected)
    frequencies = np.zeros(scorer.pair.supervisor.VOCAB, dtype=np.int64)
    for tokens, documents in subset:
        suffix = tokens[:, 1:][documents[:, :-1] == documents[:, 1:]]
        frequencies += np.bincount(suffix.numpy(), minlength=len(frequencies))
    return subset, selected, dict(profile, validation_targets=int(frequencies.sum()),
                                  group_targets={name: int(frequencies[ids].sum())
                                                 for name, ids in profile["groups"].items()})


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("arm", choices=("archive", "candidate"))
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.stop_by > END:
        parser.error("use the CPU-only device mask and the approved cutoff")
    cutoff = args.stop_by.timestamp()

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the fixed32 VAL reached its authorized cutoff")

    check()
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    native, scorer = raw.v2.native, raw.val
    profile = json.loads(native.manifest_bytes(PROFILE, PROFILE_SHA))
    if profile["source_sha256"] != raw.v1.core6.digest(Path(scorer.__file__)):
        raise ValueError("the frozen scoring source differs")
    frames, selected, scoring_profile = fixed_frames(profile)
    binding = dict(schema="P109C_FIXED32_RAW_VAL_CPU_V1", precision="CPU_FP32_MATH",
                   full_profile_sha256=PROFILE_SHA, scoring_source_sha256=profile["source_sha256"],
                   scorer_sha256=native.digest(raw.v1.core6.digest(Path(__file__))),
                   selection_batches=list(selected), windows=32, frame_sha256=scorer.frame_sha(frames),
                   targets=scoring_profile["validation_targets"])
    archive = json.loads(native.manifest_bytes(ARCHIVE_VAL, ARCHIVE_VAL_SHA))["arms"][ARCHIVE_TAG]
    archive_model = archive["model_sha256"]
    if args.arm == "candidate":
        reference = json.loads((RECORD / "archive.json").read_text(encoding="utf-8"))
        if reference["binding"] != binding or reference["model_sha256"] != archive_model:
            raise ValueError("the fixed32 archive score has different provenance")
    training = ARCHIVE_RECORD if args.arm == "archive" else CANDIDATE
    with patch.object(native, "STEPS", 2942):
        checkpoint, model_sha = raw.v2.completed_v2(training, MANIFEST_SHA)
    if (model_sha == archive_model) != (args.arm == "archive"):
        raise ValueError("the selected completed model disagrees with the expected arm")
    check()
    if args.arm == "archive":
        RECORD.mkdir(exist_ok=False)
    destination = RECORD / f"{args.arm}.json"
    if destination.exists() or destination.is_symlink():
        raise ValueError("a fixed32 score already exists")
    started = time.monotonic()
    model = raw.v1.load_model(checkpoint, 2942, "cpu")
    route = model.visit_schedule()
    with (patch.object(model.cfg, "infer_repeat", 1.), patch.object(scorer.first, "examples", return_value=())):
        if model.visit_schedule() != route:
            raise ValueError("document visibility changed the inference route")
        groups = scorer.score_model(model, frames, scoring_profile, None, check)["groups"]
    if raw.v1.core6.digest(checkpoint) != model_sha:
        raise ValueError("the evaluated weight bytes changed")
    result = dict(arm=args.arm, binding=binding, model_sha256=model_sha, groups=groups,
                  seconds=time.monotonic() - started, cpu_affinity=sorted(os.sched_getaffinity(0)),
                  torch_threads=torch.get_num_threads())
    if args.arm == "candidate":
        result["delta_nll_vs_archive"] = groups["all_valid"]["nll"] - reference["groups"]["all_valid"]["nll"]
    native.publish(destination, result)
    print(f"P109C_FIXED32_RAW_VAL_COMPLETE {args.arm}", groups["all_valid"], flush=True)


if __name__ == "__main__":
    main()
