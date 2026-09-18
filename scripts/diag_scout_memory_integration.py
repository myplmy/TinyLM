#!/usr/bin/env python3
"""P095 S0b: Scout bridge identity, causality, reset, bytes and latency."""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from tinylm.model.scout_memory import CausalScoutMemory, ScoutMemoryBridge


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--iters", type=int, default=20)
    args = parser.parse_args()
    torch.manual_seed(950)
    memory = CausalScoutMemory(slots=1024, key_dim=128, value_dim=384, dtype=torch.bfloat16)
    bridge = ScoutMemoryBridge(768, memory)
    hidden = torch.randn(args.steps, 768, requires_grad=True)
    mask = torch.tensor([index % 3 == 0 for index in range(args.steps)])

    state0 = memory.empty()
    off, state_off = bridge(hidden, state0, mask)
    assert torch.equal(off, hidden), "gate=0 fallback must be bit-identical"
    assert int(state_off.cursor) == int(mask.sum())

    bridge.gate.data.fill_(1.0)
    first, state1 = bridge(hidden, memory.empty(), mask)
    second, state2 = bridge(hidden, memory.empty(), mask)
    assert torch.equal(first, second), "reset run is not deterministic"
    assert int(state1.cursor) == int(state2.cursor) == int(mask.sum())

    perturbed = hidden.detach().clone()
    perturbed[-1].add_(100.0)
    changed, _ = bridge(perturbed, memory.empty(), mask)
    assert torch.equal(first[:-1], changed[:-1]), "future token changed prefix outputs"

    loss = first.float().square().mean()
    loss.backward()
    assert hidden.grad is not None and torch.isfinite(hidden.grad).all()
    physical = bridge.state_bytes(state1)
    logical = memory.logical_payload_bytes
    assert logical == 1_048_576
    assert physical > logical

    timings = []
    with torch.no_grad():
        for _ in range(args.iters):
            started = time.perf_counter()
            bridge(hidden.detach(), memory.empty(), mask)
            timings.append((time.perf_counter() - started) * 1e3)
    print(f"logical_payload_bytes={logical} physical_state_bytes={physical} "
          f"metadata_bytes={physical-logical}")
    print(f"steps={args.steps} writes={int(mask.sum())} "
          f"median_ms={statistics.median(timings):.4f} p95_ms={sorted(timings)[int(.95*(len(timings)-1))]:.4f}")
    print("[PASS] P095 S0b bridge: default-off identity, reset determinism, prefix invariance, "
          "physical accounting, finite backward")
    print("NOTE: full Transformer wiring, context-shortcut dataset, learned WRITE and quality remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
