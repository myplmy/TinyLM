#!/usr/bin/env python3
"""P097 Stage2 fail-closed asset gate; model/GPU/network execution: 0."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODELS = ("p097_ctrl_v2", "p097_fw2", "p097_edu_v2", "p097_madlad")
DEFAULT_DATA = ("ko-en-control-v2", "ko-en-fw2", "ko-en-edu-v2", "ko-en-madlad")
DEFAULT_TASKS = (
    "kobest_copa", "kobest_hellaswag", "klue_ynat", "klue_nli",
    "arc_easy_full", "hellaswag",
)


def expected_paths(preset, tokens, models, datas, tasks):
    checkpoints = [
        ROOT / "runs" / "ckpt" / f"{preset}_{data}_{tokens}_{tag}.pt"
        for tag, data in zip(models, datas)
    ]
    logs = [
        ROOT / "runs" / "logs" / f"{preset}_{data}_{tokens}_{tag}.json"
        for tag, data in zip(models, datas)
    ]
    benches = [ROOT / "datasets" / "bench" / f"{task}.jsonl" for task in tasks]
    common_text = ROOT / "datasets" / "squad" / "train-v2.0.json"
    return checkpoints, logs, benches, common_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", default="m100s10")
    parser.add_argument("--tokens", default="300M")
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--model-data", nargs="+", default=list(DEFAULT_DATA))
    parser.add_argument("--tasks", nargs="+", default=list(DEFAULT_TASKS))
    parser.add_argument("--outputs", nargs="*", default=[])
    args = parser.parse_args()
    if len(args.models) != len(args.model_data):
        parser.error("--models and --model-data must have the same length")

    checkpoints, logs, benches, common_text = expected_paths(
        args.preset, args.tokens, args.models, args.model_data, args.tasks
    )
    missing = [path for path in checkpoints + logs + benches + [common_text] if not path.is_file()]
    occupied = [ROOT / value for value in args.outputs if (ROOT / value).exists()]
    for path in checkpoints:
        print(f"[{'PASS' if path.is_file() else 'MISS'}] checkpoint {path.relative_to(ROOT)}")
    for path in logs:
        print(f"[{'PASS' if path.is_file() else 'MISS'}] train-json {path.relative_to(ROOT)}")
    for path in benches:
        print(f"[{'PASS' if path.is_file() else 'MISS'}] benchmark {path.relative_to(ROOT)}")
    print(f"[{'PASS' if common_text.is_file() else 'MISS'}] common-bpb {common_text.relative_to(ROOT)}")
    for path in occupied:
        print(f"[STOP] output already exists; refusing append/overwrite: {path.relative_to(ROOT)}")
    if missing:
        task_names = [path.stem for path in benches if not path.is_file()]
        if task_names:
            print("[NEXT] fetch missing public benchmarks under repo HF cache:")
            print("  python scripts/fetch_bench_data.py --only " + " ".join(task_names))
        print(f"[GATE FAIL] missing assets={len(missing)}")
        return 2
    if occupied:
        return 3
    print("[PASS] P097 Stage2 assets: four exact checkpoints/tokenizers, six panels, common text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
