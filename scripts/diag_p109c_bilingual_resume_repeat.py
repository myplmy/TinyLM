"""Measure native CUDA repeatability from the exact earlier bilingual checkpoint."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

import torch

from scripts import diag_p109c_bilingual_native_resume as original


prep, native, inputs = original.prep, original.native, original.inputs
TAG = "p109c_bilingual_aux_resume_repeat_cuda_v2_20261124"
RECORD = prep.EVIDENCE / TAG
PRIOR = prep.EVIDENCE / original.TAG
TRIALS = 3
EXPECTED_FIELDS = ("source_update", "actual_forwards", "reserved_batches", "empty_batches", "forward_layer_slots",
                   "raw_targets", "course_inputs", "answer_targets", "location_targets", "context_targets")


def prepare():
    proof, terminal = PRIOR / "report.json", PRIOR / "supervisor.json"
    report, completion = prep.read_json(proof), prep.read_json(terminal)
    if (report["status"] != "NATIVE_CHECKPOINT_RECOVERY_MEASURED"
            or not all(report["matched_discrete_state"].values()) or completion["returncode"] != 0
            or completion["stop_reason"] is not None or completion["card_after_exit"]["compute_pids"] != []):
        raise ValueError("the source experiment needs a measured, returned checkpoint")
    source = Path(report["prefix"]["path"])
    if source.parent != PRIOR / "ckpt" or source.resolve(strict=True) != source:
        raise ValueError("the repeat must read the original unlinked checkpoint")
    checksum = prep.sha(source)
    if checksum != report["prefix"]["sha256"]:
        raise ValueError("the original bilingual checkpoint changed")
    saved = torch.load(source, map_location="cpu", mmap=True, weights_only=True)
    context = original.checkpoint_context(saved, report["sealed"], original.BOUNDARY)
    rows = report["continuous_updates"][:original.BOUNDARY]
    journal_sha = sha256(b"".join(original.encode(row) for row in rows)).hexdigest().upper()
    if (saved[original.SAVE_KEY] != dict(step=original.BOUNDARY, journal_sha256=journal_sha)
            or context["payload_sha256"] != report["prefix"]["native_payload_sha256"]):
        raise ValueError("the saved checkpoint and the original prefix journal disagree")
    runner = Path(__file__).resolve()
    profile = dict(tag=TAG, trials=TRIALS, source=str(source), checkpoint_sha256=checksum,
                   native_payload_sha256=context["payload_sha256"], journal_sha256=journal_sha,
                   original_report=prep.sha(proof), original_supervisor=prep.sha(terminal),
                   original_inputs=report["sealed"], source_sha256=prep.sha(runner))
    return profile, report, dict(path=source, rows=rows)


def compare(left, right):
    a, b = (state[original.objective.trainer.CONTEXT_STATE_KEY] for state in (left, right))
    discrete = {key: a[key] == b[key] for key in ("cursor", "binding", "validation_rng")}
    discrete.update({key: torch.equal(a[key], b[key]) for key in ("cpu_rng", "cuda_rng")})
    if not all(discrete.values()):
        raise ValueError("the saved-file repeats reached different bindings, inputs or RNG state")
    numeric = {key: original.differences(left[key], right[key]) for key in original.NUMERIC_STATE}
    for entry in numeric.values():
        entry["relative_l2"] = entry["difference_l2"] / entry["reference_l2"] if entry["reference_l2"] else None
    return dict(discrete=discrete, numeric=numeric,
                last_validation=[a["control"]["history"][-1]["val_loss"], b["control"]["history"][-1]["val_loss"]])


def worker(receipt, digest, _resume, record, cutoff):
    with (inputs.training.locked_record(record),
          (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress,
          redirect_stdout(log), redirect_stderr(log)):
        sealed = json.loads(native.manifest_bytes(receipt, digest))
        checked, prior, prefix = prepare()
        profile, bundle, slots = original.prepare()
        if sealed != checked or profile != checked["original_inputs"] or torch.cuda.device_count() != 1:
            raise ValueError("the original optimizer inputs or approved device have changed")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        free, total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("the CUDA allocation budget is unavailable")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        reference = None
        comparisons = []
        for index in range(TRIALS):
            arm = record / f"repeat_{index + 1}"
            (arm / "ckpt").mkdir(parents=True)
            (arm / "native_logs").mkdir()
            destination = arm / "ckpt" / prefix["path"].name
            shutil.copyfile(prefix["path"], destination)
            if prep.sha(destination) != checked["checkpoint_sha256"]:
                raise ValueError("the regular-file resume copy differs from the admitted checkpoint")
            print(json.dumps(dict(start=index + 1)), file=progress, flush=True)
            current, rows, _ = original.run_arm(arm, cutoff, profile, bundle, slots, progress, prefix)
            if any(a[key] != b[key] for a, b in zip(rows, prior["resumed_updates"], strict=True)
                   for key in EXPECTED_FIELDS):
                raise ValueError("a replay did not apply the originally audited supervision")
            if reference is None:
                reference = current
            else:
                comparisons.append(dict(repeat=index + 1, **compare(reference, current)))
            del current
            gc.collect()
            torch.cuda.empty_cache()
        bundle.unchanged()
        if prep.sha(prefix["path"]) != checked["checkpoint_sha256"]:
            raise ValueError("the source checkpoint changed during the comparison")
        native.publish(record / "report.json", dict(profile=checked,
                       previous_continuous_vs_resume=prior["resume_comparison"], comparisons=comparisons,
                       peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                       actual_replayed_updates=TRIALS * (len(original.ADDRESSES) - original.BOUNDARY)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        profile, _, _ = prepare()
        native.publish(args.profile, profile)
        print(prep.sha(args.profile), flush=True)
        return 0
    if (args.profile_sha256 is None or args.stop_by is None or not args.stop_by.tzinfo
            or args.stop_by > inputs.AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"
            or (args.stop_by - datetime.now(args.stop_by.tzinfo)).total_seconds() < 150):
        parser.error("the sealed receipt, exclusive GPU 0 and authorized time are required")
    return inputs.supervisor.supervise(worker, args.profile.absolute(), args.profile_sha256, RECORD, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
