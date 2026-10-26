#!/usr/bin/env python3
"""Read only the latest complete update; do not evaluate partial models."""
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[3]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("format_muon", "format_normuon"), required=True)
    args = parser.parse_args()
    folder = ROOT / "test_result/evidence" / ("p106b_native_format_training_v1_20261026_" + args.arm + "_train")
    shards = sorted((folder / "updates").glob("updates_*.jsonl"))
    latest = None
    if shards:
        path = shards[-1]
        with path.open("rb") as stream:
            start = max(0, path.stat().st_size - 65536)
            stream.seek(start)
            lines = stream.read().splitlines()
        for line in lines[1:] if start else lines:
            try:
                latest = json.loads(line)
            except json.JSONDecodeError:
                pass
    report = {"arm": args.arm, "updates_total": 2289, "full_targets": 300023808,
        "latest_update": None if latest is None else latest["update"],
        "last_step_seconds": None if latest is None else latest["step_seconds"],
        "root_closed": (folder / "root_closed_ref.json").is_file(),
        "partial_quality_evaluation": False}
    print(json.dumps(report))

if __name__ == "__main__":
    main()
