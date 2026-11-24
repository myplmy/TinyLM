"""Diagnose first-position EOT separately from answer content on frozen DEV."""

import argparse
from datetime import datetime
import os
from pathlib import Path
from time import perf_counter, time
from types import SimpleNamespace

from scripts import eval_p109c_completed as completed
from scripts import eval_p109c_native_final200_cpu as comparison
from scripts.p106b_shards import ShardWriter, verify


def emit_without_first_eot(active, question, max_new):
    model, _, _ = active

    def filter_first(_module, _args, output):
        handle.remove()
        logits, past = output
        logits = logits.clone()
        logits[:, -1, 4] = -float("inf")
        return logits, past

    handle = model.register_forward_hook(filter_first)
    try:
        return comparison.emit(active, question, max_new)
    finally:
        handle.remove()


def evaluate(args):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    def check():
        if time() >= args.stop_by.timestamp():
            raise TimeoutError("the CPU DEV check reached its cutoff")

    check()
    profile_path = completed.regular_file(args.profile.absolute())
    profile = completed.read_json(profile_path)
    if (completed.core6.digest(profile_path) != args.profile_sha256.upper()
            or completed.source_pins() != profile["sources"]):
        raise ValueError("the pinned evaluation inputs differ")
    manifest_path = completed.regular_file(completed.FINAL200 / "manifest.json")
    manifest = completed.read_json(manifest_path)
    dev_path = completed.regular_file(completed.FINAL200 / "dev.json")
    cases = completed.read_json(dev_path)
    if (completed.core6.digest(manifest_path) != completed.FINAL200_SHA
            or comparison.protocol.data.digest(cases) != manifest["contract"]["dev_sha256"]
            or len(cases) != 20 or any(row["split"] != "dev" for row in cases)):
        raise ValueError("the frozen DEV-only cohort differs")
    checkpoint, stamp = completed.completed_checkpoint(Path(profile["training_record"]),
                                                       profile["training_manifest_sha256"])
    source_files = (Path(__file__), Path(comparison.__file__), Path(comparison.protocol.__file__),
                    Path(comparison.manual.__file__), dev_path)
    pins = {str(p.resolve()): completed.core6.digest(p) for p in source_files}
    model_before = completed.training.file_stamp(checkpoint)
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    active = (completed.load_model(checkpoint, completed.training.STEPS, "cpu"),
              completed.load_tokenizer(), SimpleNamespace(assert_active=check))
    record = args.record.absolute()
    record.mkdir(parents=True, exist_ok=False)
    report = dict(status="STARTED", model=completed.MODEL_NAME, checkpoint_sha256=stamp,
                  dev_sha256=manifest["contract"]["dev_sha256"], precision="CPU_FP32_MATH",
                  target_id=4, target_generated_step=0, sources=pins, arms={})
    started = perf_counter()
    try:
        with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
            for arm, emit in (("baseline", comparison.emit), ("first_step_without_eot", emit_without_first_eot)):
                receiver = ShardWriter(record, arm)
                arm_report = dict(model=completed.MODEL_NAME, completed_rows=0)
                comparison.protocol.collect(active, cases, receiver, SimpleNamespace(check=check), arm_report, emit=emit)
                arm_report["answers"] = receiver.close(lineage=dict(split="dev", arm=arm, checkpoint_sha256=stamp))
                verify(record, arm_report["answers"])
                report["arms"][arm] = arm_report
        if (completed.training.file_stamp(checkpoint) != model_before
                or completed.source_pins() != profile["sources"]
                or any(completed.core6.digest(Path(path)) != sha for path, sha in pins.items())):
            raise ValueError("a pinned source or weight file changed")
        report["status"] = "RESPONSES_COMPLETE_SEMANTIC_REVIEW_NOT_RUN"
    except Exception as error:
        report.update(status="ERROR", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["seconds"] = perf_counter() - started
        completed.training.publish(record / "report.json", report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None:
        parser.error("a CPU-only environment and an explicit cutoff timezone are required")
    evaluate(args)


if __name__ == "__main__":
    main()
