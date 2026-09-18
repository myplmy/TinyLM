#!/usr/bin/env python3
"""Checkpoint catalog discovery/selection regression without model loading."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.infer.catalog import discover_models, filter_models, resolve_selection


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="model-catalog-") as temporary:
        root = Path(temporary)
        ckpt, logs = root / "ckpt", root / "logs"
        ckpt.mkdir(); logs.mkdir()
        stem = "m100s10_ko-en_300M_fixture"
        (ckpt / f"{stem}.pt").write_bytes(b"")
        (ckpt / f"{stem}_best.pt").write_bytes(b"")
        (logs / f"{stem}.json").write_text(json.dumps({
            "preset": "m100s10", "data": "ko-en", "arch": "dense",
            "steps": 2289, "pool_tokens": 600_000_000, "seed": 1337,
            "optimizer": "muon", "final": {"val_loss": 3.5}, "best_val": 3.4,
        }), encoding="utf-8")
        rows = discover_models(ckpt, logs)
        assert len(rows) == 2
        assert rows[0].is_best and rows[0].display_val == 3.4
        assert resolve_selection(rows, "1") == rows[0]
        assert resolve_selection(rows, "fixture_best").is_best
        assert len(filter_models(rows, "m100s10")) == 2
    print("[PASS] model catalog: metadata join, best/final score, number/tag selection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
