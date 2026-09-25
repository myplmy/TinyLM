#!/usr/bin/env python3
"""CPU-only exit-code contract for the P060B Stage2b GQA attribution gate."""
from __future__ import annotations

from diag_sdpa_gqa_deploy_attribution import gate_status


def case(**changes: object) -> int:
    values = {
        "backend_failed": False,
        "agreement_failed": False,
        "text_failed": False,
        "ratios": [1.0],
        "reductions": [0.10],
        "slowdown_limit": 1.05,
        "min_benefit": 0.05,
    }
    values.update(changes)
    return gate_status(**values)


def main() -> int:
    assert case(backend_failed=True, agreement_failed=True) == 5
    assert case(agreement_failed=True) == 4
    assert case(text_failed=True) == 4
    assert case(ratios=[]) == 4
    assert case(ratios=[1.06]) == 8
    assert case(ratios=[1.0], reductions=[0.0]) == 8
    assert case(ratios=[1.0], reductions=[0.10]) == 0
    assert case(ratios=[0.90], reductions=[0.0]) == 0
    print("[PASS] P060B Stage2b exit=0 candidate, 4 agreement, 5 runtime, 8 valid negative")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
