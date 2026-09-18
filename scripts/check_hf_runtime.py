#!/usr/bin/env python3
"""Runtime assertion that every Hugging Face cache path stays under repo/HF."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tinylm  # noqa: F401  # applies redirect
from tinylm import paths


def main() -> int:
    expected = paths.HF_DIR.resolve()
    variables = {
        "HF_HOME": expected,
        "HF_HUB_CACHE": (expected / "hub").resolve(),
        "HF_DATASETS_CACHE": (expected / "datasets").resolve(),
    }
    errors = []
    for name, wanted in variables.items():
        actual = Path(os.environ.get(name, "")).resolve()
        print(f"{name}={actual}")
        if actual != wanted:
            errors.append(f"{name}: {actual} != {wanted}")
        try:
            actual.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{name}: repository 밖 경로")
    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 3
    print(f"[PASS] all Hugging Face cache paths are under {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
