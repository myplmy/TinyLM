"""Measure FINAL200 with the original P109C weights and genuine FP32 generation."""

import argparse
from datetime import datetime
import os
from pathlib import Path
from time import perf_counter, time
from types import SimpleNamespace

from scripts import eval_p109c_completed as completed
from scripts import eval_p109c_native_final200_cpu as comparison
from scripts.p106b_shards import ShardWriter, verify


def evaluate(profile_path, expected_profile, record, cutoff):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    def check_time():
        if time() >= cutoff:
            raise TimeoutError("the FP32 comparison reached its cutoff")

    check_time()
    profile_path = completed.regular_file(profile_path)
    if completed.core6.digest(profile_path) != expected_profile:
        raise ValueError("the official evaluation profile fingerprint differs")
    profile = completed.read_json(profile_path)
    if completed.source_pins() != profile["sources"]:
        raise ValueError("the official evaluation source fingerprints differ")
    checkpoint, stamp = completed.completed_checkpoint(Path(profile["training_record"]),
                                                       profile["training_manifest_sha256"])
    checkpoint_stat = completed.training.file_stamp(checkpoint)
    cases, contract = completed.final200_inputs()
    helpers = (Path(__file__), Path(comparison.__file__), Path(comparison.protocol.__file__),
               Path(comparison.manual.__file__), Path(comparison.__file__).parent / "p106b_shards.py")
    source_pins = {str(path.resolve()): completed.core6.digest(path) for path in helpers}
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    tokenizer = completed.load_tokenizer()
    model = completed.load_model(checkpoint, completed.training.STEPS, "cpu")

    def check_model():
        if model.training or next(model.parameters()).dtype != torch.float32:
            raise RuntimeError("FP32 inference is required")

    record.mkdir(parents=True, exist_ok=False)
    report = dict(status="STARTED", model=completed.MODEL_NAME, checkpoint_sha256=stamp,
                  profile_sha256=expected_profile, final_input_sha256=contract["final_sha256"],
                  device="cpu", precision="FP32_MATH", max_new=comparison.protocol.data.MAX_NEW,
                  sources=source_pins, completed_rows=0)
    writer = ShardWriter(record, "responses")
    started = perf_counter()
    try:
        with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
            comparison.protocol.collect((model, tokenizer, SimpleNamespace(assert_active=check_model)),
                                        cases, writer, SimpleNamespace(check=check_time), report,
                                        emit=comparison.emit)
        if (report["completed_rows"] != len(cases)
                or completed.training.file_stamp(checkpoint) != checkpoint_stat
                or completed.source_pins() != profile["sources"]
                or any(completed.core6.digest(Path(path)) != sha for path, sha in source_pins.items())):
            raise ValueError("the answers, weights or evaluation sources differ")
        report["status"] = "RESPONSES_COMPLETE_SEMANTIC_REVIEW_NOT_RUN"
    except Exception as error:
        report.update(status="ERROR", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        report["seconds"] = perf_counter() - started
        if report["completed_rows"]:
            report["answers"] = writer.close(lineage=dict(model=completed.MODEL_NAME,
                                                           checkpoint_sha256=stamp,
                                                           precision="FP32_MATH"))
            verify(record, report["answers"])
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
    evaluate(args.profile.absolute(), args.profile_sha256.upper(), args.record.absolute(),
             args.stop_by.timestamp())


if __name__ == "__main__":
    main()
