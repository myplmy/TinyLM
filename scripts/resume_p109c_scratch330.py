"""Resume the admitted P109C run into a separate record from a full native checkpoint."""

import argparse
from datetime import datetime
from functools import partial
import json
from pathlib import Path
import shutil
import subprocess
import time
from unittest.mock import patch

from scripts import run_p109c_scratch330 as entry
from scripts import run_p109c_with_aoa_archive as archived
from tinylm.train import trainer


def inspect(checkpoint, expected, step, manifest_sha, prior_record):
    import torch
    from tinylm.train.context_training_state import validate_trainer_control

    if checkpoint.resolve(strict=True) != checkpoint or entry.file_sha(checkpoint).upper() != expected:
        raise ValueError("the original resume checkpoint identity differs")
    prior = json.loads((prior_record / "supervisor.json").read_bytes())
    original_input = json.loads((prior_record / "input.json").read_bytes())
    if (not prior["returncode"] or not prior["stop_reason"] or (prior_record / "evaluation.pt").exists()
            or original_input["manifest_sha256"] != manifest_sha or not original_input["ste_per_micro"]):
        raise ValueError("resume requires the same interrupted and incomplete STE run")
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    context = saved[trainer.CONTEXT_STATE_KEY]
    cursor = context["cursor"]["cursor"]
    control = context["control"]
    recipe = context["binding"]["recipe"]
    slots = step * entry.MICRO * entry.ACCUM * entry.WIDTH
    if (not 0 < step < entry.BOUNDARY or saved["step"] != step or cursor["optimizer_updates"] != step
            or cursor["next_update"] != step or cursor["draw_tokens"] != slots or cursor["ntp_targets"] != slots
            or recipe["p109c_input_manifest"] != manifest_sha or control["n_skip"]
            or saved["ce_recompute_rows"] != 1024 or not saved["opt"]["state"]
            or not saved["opt_muon"]["state"] or context["cuda_rng"] is None):
        raise ValueError("the checkpoint requires the exact full original-phase resume state")
    validate_trainer_control(control, step, cursor["optimizer_updates"])
    return dict(schema="P109C_FULL_NATIVE_RESUME_V1", original_record=str(prior_record),
                original_pid=prior["pid"], original_checkpoint=str(checkpoint), original_checkpoint_sha256=expected,
                manifest_sha256=manifest_sha, step=step, optimizer_updates=cursor["optimizer_updates"],
                draw_slots=slots, ntp_targets=cursor["ntp_targets"], source_calls=cursor["source_calls"],
                adamw_states=len(saved["opt"]["state"]), muon_states=len(saved["opt_muon"]["state"]),
                context_state_sha256=context["payload_sha256"], native_binding_sha256=context["binding"]["binding_sha256"],
                best_step=control["best_step"], best_val=control["best_val"], skipped_updates=control["n_skip"])


def worker(checkpoint, expected, step, prior_record, path, sha256, resume, record, cutoff,
           *, reuse_quantization):
    if not resume or not reuse_quantization:
        raise ValueError("the continuation requires native resume and STE reuse")
    proof = inspect(checkpoint, expected, step, entry.digest(sha256), prior_record)
    checkpoint_root = record / "native_ckpt"
    log_root = record / "native_logs"
    checkpoint_root.mkdir(exist_ok=False)
    native = checkpoint_root / checkpoint.name
    shutil.copyfile(checkpoint, native)
    if entry.file_sha(native).upper() != expected:
        raise ValueError("the copied resume checkpoint differs")
    entry.publish(record / "resume_prefix.json", proof)
    with patch.object(trainer, "CKPT", checkpoint_root), patch.object(trainer, "LOGS", log_root):
        archived.worker(path, sha256, resume, record, cutoff, reuse_quantization=reuse_quantization)


def sample_with_retry(read, record):
    for attempt in range(3):
        try:
            return read()
        except subprocess.CalledProcessError as error:
            if error.returncode != 255 or attempt == 2:
                raise
            with (record / "telemetry_retries.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps(dict(time=time.time(), attempt=attempt + 1, exit_code=error.returncode)) + "\n")
            time.sleep(.35 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--prior-record", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    checksum = entry.digest(args.checkpoint_sha256)
    manifest_sha = entry.digest(args.manifest_sha256)
    entry.manifest_bytes(args.manifest.absolute(), manifest_sha)
    original = args.checkpoint.absolute()
    prior = args.prior_record.absolute()
    if original.name != f"{entry.PRESET}_ko-en_330M_{entry.TAG}.pt":
        raise ValueError("the checkpoint filename is outside the exact original run")
    if args.mode == "check":
        print(json.dumps(inspect(original, checksum, args.step, manifest_sha, prior), indent=2))
        return 0
    if args.record is None or args.stop_by is None:
        parser.error("run requires a new --record and --stop-by")
    record = args.record.absolute()
    with (patch.object(entry, "gpu_worker", partial(worker, original, checksum, args.step, prior)),
          patch.object(entry, "gpu_status", partial(sample_with_retry, entry.gpu_status, record))):
        return entry.supervise(args.manifest.absolute(), manifest_sha, True, record, args.stop_by,
                               reuse_quantization=True)


if __name__ == "__main__":
    raise SystemExit(main())
