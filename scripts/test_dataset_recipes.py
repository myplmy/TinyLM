#!/usr/bin/env python3
"""Network-free contracts for P097 dataset recipes."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.data.prepare import DATASETS, TOKEN_BALANCED_DATASETS, exact_token_quotas


def main() -> int:
    expected = {"ko-en-control-v2", "ko-en-fw2", "ko-en-edu-v2", "ko-en-madlad"}
    assert TOKEN_BALANCED_DATASETS == expected
    assert expected <= set(DATASETS)
    assert exact_token_quotas(600_000_000, [0.5, 0.5]) == [300_000_000, 300_000_000]
    assert exact_token_quotas(11, [1, 1, 1]) == [3, 3, 5]
    for name in expected:
        specs = DATASETS[name]
        assert len(specs) == 2
        assert all(len(spec) == 5 and spec[3] == "text" for spec in specs)
        assert sum(spec[4] for spec in specs) == 1.0
    print("[PASS] P097 recipes: isolated names, exact quotas, text schemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
