"""Score the unfinished HellaSwag task with the same official FP32 bridge on CPU."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sysconfig
import time
from types import SimpleNamespace
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import eval_p109c_mixed_v2 as common
from scripts.p106b_official_lm_adapter import create_adapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None:
        parser.error("a CPU-only environment and authorized cutoff are required")
    torch.set_num_threads(6)
    torch.set_num_interop_threads(1)
    original, native = common.original, common.native
    path, cutoff = args.profile.absolute(), args.stop_by.timestamp()
    profile = json.loads(native.manifest_bytes(path, args.profile_sha256))

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the CPU HellaSwag evaluation reached its authorized cutoff")

    check()
    if profile["sources"] != common.pinned_sources():
        raise ValueError("the sealed official evaluation source changed")
    train = Path(profile["training_record"])
    end = original.read_json(train / "input.json")["steps"]
    with patch.object(native, "STEPS", end):
        checkpoint, stamp = common.completed_v2(train, profile["training_manifest_sha256"])
    inputs, signature = original.load_inputs(("core6",))
    if json.loads(json.dumps(signature["core6"])) != profile["inputs"]["core6"]:
        raise ValueError("the official HellaSwag input contract differs")
    model = original.load_model(checkpoint, end, "cpu")
    runtime = dict(torch=torch, model=model, cfg=model.cfg, tokenizer=original.load_tokenizer(),
                   precision="FP32_MATH", checkpoint=str(checkpoint), checkpoint_sha256=stamp,
                   tokenizer_sha256=original.TOKENIZER_SHA)
    adapter = create_adapter(runtime, runtime_root=Path(sysconfig.get_paths()["purelib"]), batch_size=8)
    from lm_eval import evaluator

    evaluate = evaluator.simple_evaluate

    def on_cpu(**options):
        return evaluate(**dict(options, device="cpu"))

    oracle = SimpleNamespace(tensor=lambda *a, **k: torch.tensor(*a, **dict(k, device="cpu")),
                             long=torch.long, float32=torch.float32, nn=torch.nn)

    record = args.record.absolute()
    record.mkdir(exist_ok=False)
    started = time.monotonic()
    count = original.core6.TASK_COUNTS["hellaswag"]
    try:
        with (torch.no_grad(), sdpa_kernel(SDPBackend.MATH),
              patch.object(original.core6, "TASK_COUNTS", {"hellaswag": count}),
              patch.object(original, "MODEL_NAME", common.MODEL_NAME),
              patch.object(evaluator, "simple_evaluate", on_cpu)):
            canary = original.core6.numerical_canary(adapter, oracle)
            scores = original.evaluate_core6(adapter, inputs["core6"], record, check)
        if original.core6.digest(checkpoint) != stamp:
            raise ValueError("the completed P109C evaluation weights changed")
        native.publish(record / "report.json", dict(status="COMPLETE", backend="CPU_FP32_MATH",
                       checkpoint_sha256=stamp, profile_sha256=args.profile_sha256.upper(),
                       task="hellaswag", rows=count, model=common.MODEL_NAME, canary=canary,
                       official=scores["hellaswag"], seconds=time.monotonic()-started))
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
