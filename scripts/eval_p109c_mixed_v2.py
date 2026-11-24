"""Evaluate the completed P109C v2 body on the already-frozen P109C comparison suite."""

import argparse
from datetime import datetime
from functools import partial
import json
from pathlib import Path
from unittest.mock import patch

from scripts import eval_p109c_completed as original
from scripts import p109_gpu_supervisor as telemetry
from scripts import run_p109c_scratch330 as native
from scripts import wait_p109_cuda_return as returned


MODEL_NAME = "p109c-scratch-mixed-v2"
GROUPS = ("first_use", "final200", "core6", "korean_choices")


def pinned_sources():
    result = original_pins()
    path = Path(__file__).resolve()
    result[str(path.relative_to(original.ROOT))] = original.core6.digest(path)
    return result


original_pins = original.source_pins


def completed_v2(path, checksum):
    source = original.read_json(original.regular_file(path / "input.json"))
    terminal = original.read_json(original.regular_file(path / "supervisor.json"))
    closed = original.read_json(original.regular_file(path / "report.json"))
    result = original.read_json(original.regular_file(path / "training.json"))
    checkpoint = original.regular_file(path / "evaluation.pt")
    stamp = original.core6.digest(checkpoint)
    end = source["steps"]
    rows = result["updates"]
    if (terminal["returncode"] != 0 or terminal["stop_reason"] is not None
            or terminal["card_after_exit"]["compute_pids"] != []
            or closed["status"] != "FULL_SCRATCH_MIXED_COMPLETE" or closed["steps"] != end
            or source["manifest_sha256"] != checksum or closed["input_manifest_sha256"] != checksum
            or result["input_manifest_sha256"] != checksum or result["evaluation_sha256"] != stamp
            or closed["evaluation_sha256"] != stamp or not rows
            or rows[-1]["index"] + 1 != end or any(not row["optimizer_applied"] for row in rows)):
        raise ValueError("the sealed v2 model and its continuous optimizer completion do not agree")
    if end != native.STEPS:
        raise ValueError("the frozen evaluation step differs from the completed v2 run")
    return checkpoint, stamp


def worker(end, profile, checksum, resume, record, cutoff):
    with (patch.object(native, "STEPS", end),
          patch.object(original, "MODEL_NAME", MODEL_NAME),
          patch.object(original, "completed_checkpoint", completed_v2),
          patch.object(original, "source_pins", pinned_sources)):
        original.worker(profile, checksum, resume, record, cutoff)


def prepare(path, train_dir, manifest_sha, groups):
    original.load_tokenizer()
    _, proofs = original.load_inputs(groups)
    pins = pinned_sources()
    native.publish(path, dict(schema="P109C_MIXED_V2_COMPLETED_EVALUATION_V1",
        training_record=str(train_dir), training_manifest_sha256=native.digest(manifest_sha),
        groups=groups, inputs=proofs, sources=pins, policy=original.core6.policy()))
    print("P109C_MIXED_EVAL_PROFILE_READY", path, original.core6.digest(path), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    plan = sub.add_parser("prepare")
    plan.add_argument("--training-record", required=True, type=Path)
    plan.add_argument("--training-manifest-sha256", required=True)
    plan.add_argument("--profile", required=True, type=Path)
    plan.add_argument("--groups", nargs="+", choices=GROUPS, default=GROUPS)
    run = sub.add_parser("run")
    run.add_argument("--profile", required=True, type=Path)
    run.add_argument("--profile-sha256", required=True)
    run.add_argument("--record", required=True, type=Path)
    run.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    profile_path = args.profile.absolute()
    if args.action == "prepare":
        if len(set(args.groups)) != len(args.groups):
            parser.error("each evaluation group can run only once")
        prepare(profile_path, args.training_record.absolute(), args.training_manifest_sha256, args.groups)
        return 0
    if args.stop_by.tzinfo is None:
        parser.error("the evaluation cutoff needs a timezone")
    sealed = json.loads(native.manifest_bytes(profile_path, args.profile_sha256))
    if sealed["schema"] != "P109C_MIXED_V2_COMPLETED_EVALUATION_V1" or sealed["sources"] != pinned_sources():
        raise ValueError("the frozen v2 evaluation profile or source differs")
    train_dir = Path(sealed["training_record"])
    terminal = original.read_json(original.regular_file(train_dir / "supervisor.json"))
    returned.wait_for_return(train_dir / "supervisor.json", terminal["pid"], args.stop_by)
    end = original.read_json(original.regular_file(train_dir / "input.json"))["steps"]
    with patch.object(native, "STEPS", end):
        completed_v2(train_dir, sealed["training_manifest_sha256"])
    record = args.record.absolute()
    with (patch.object(native, "gpu_worker", partial(worker, end)),
          patch.object(native, "gpu_status", partial(telemetry.gpu_status, record))):
        return native.supervise(profile_path, args.profile_sha256, False, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
