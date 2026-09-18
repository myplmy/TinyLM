#!/usr/bin/env python3
"""P093 Stage0a/0b — duplicate routing and no-GPU sharing accounting."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tinylm.config import build_config  # noqa: E402
from tinylm.train.sharing_accounting import (  # noqa: E402
    _packed_matrix_bytes,
    account_candidate,
    standard_candidates,
)


OVERLAP = {
    "E0-g2": ("CLOSED", "P045B result 079 already rejects same-width exact g2"),
    "D1-wide-core": ("NEW", "wider shared core is not the P045B question"),
    "D2-use-normalized": ("DEPENDENCY", "optimizer use-count audit is owned by P091"),
    "D3-cycle": ("DUPLICATE_HOLD", "P061/P074 schedule equivalence audit precedes any run"),
    "R1-depth-lowrank-r4": ("NEW", "persistent depth residual differs from P008 removal LoRA"),
    "R1-depth-lowrank-r8": ("NEW", "persistent depth residual differs from P008 removal LoRA"),
    "R1-depth-lowrank-r16": ("NEW", "persistent depth residual differs from P008 removal LoRA"),
}


def main() -> int:
    # Regression: g128 owns two fp16 scales across a 256-wide row, whereas
    # per-row/g256 owns one.  A previous branch typo made both paths per-row.
    assert _packed_matrix_bytes(1, 256, 128) > _packed_matrix_bytes(1, 256, 256)

    cfg = build_config("m100", "tied", 1024, True)
    candidates = standard_candidates(cfg)
    dense = account_candidate(cfg, candidates[0])
    dense = account_candidate(cfg, candidates[0], dense)

    print("candidate\toverlap\tpacked_MiB\tsaving\textra_flops\toptimizer_MiB\ttrack")
    seen = set()
    for candidate in candidates[1:]:
        assert candidate.candidate_id not in seen
        seen.add(candidate.candidate_id)
        status, _reason = OVERLAP[candidate.candidate_id]
        row = account_candidate(cfg, candidate, dense)
        passes_memory = row.deployment_saving_ratio >= 0.15
        passes_flops = row.extra_flops_ratio <= 0.10
        if status in {"CLOSED", "DUPLICATE_HOLD"}:
            track = status
        elif not passes_memory:
            track = "REJECT_MEMORY"
        elif not passes_flops:
            track = "HIGH_COMPUTE_PARETO"
        elif status == "DEPENDENCY":
            track = "WAIT_P091"
        else:
            track = "BASE_PARETO"
        print(
            f"{candidate.candidate_id}\t{status}\t{row.packed_bytes / 2**20:.3f}\t"
            f"{row.deployment_saving_ratio:.3%}\t{row.extra_flops_ratio:.3%}\t"
            f"{row.optimizer_state_bytes / 2**20:.3f}\t{track}"
        )

    assert OVERLAP["E0-g2"][0] == "CLOSED"
    assert OVERLAP["D3-cycle"][0] == "DUPLICATE_HOLD"
    assert any(
        account_candidate(cfg, candidate, dense).deployment_saving_ratio >= 0.15
        and account_candidate(cfg, candidate, dense).extra_flops_ratio <= 0.10
        for candidate in candidates if candidate.candidate_id.startswith("R1-")
    )
    d1 = next(candidate for candidate in candidates if candidate.candidate_id == "D1-wide-core")
    assert account_candidate(cfg, d1, dense).extra_flops_ratio > 0.10
    print("[PASS] P093 Stage0a/0b: overlap, unique weights, packed/resident/state/FLOPs accounted")
    print("NOTE: activation memory, allocator RSS, latency, model quality and GPU execution remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
