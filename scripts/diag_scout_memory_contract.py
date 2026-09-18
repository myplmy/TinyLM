#!/usr/bin/env python3
"""P095 S0 — causal isolation, byte cap, gradient 계약(CPU)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from tinylm.model.scout_memory import CausalScoutMemory


def rollout(memory, writes):
    state = memory.empty()
    outputs = []
    for key, value in writes:
        read, _weights, state = memory.step(key, key, value, state)
        outputs.append(read)
    return outputs, state


def main() -> int:
    memory = CausalScoutMemory()
    assert memory.logical_payload_bytes == 1024 * 1024

    key_a = torch.zeros(128); key_a[0] = 4
    key_b = torch.zeros(128); key_b[1] = 4
    value_a = torch.zeros(384); value_a[0] = 3
    value_b = torch.zeros(384); value_b[1] = 5

    state0 = memory.empty()
    first, _weights, state1 = memory.step(key_a, key_a, value_a, state0)
    assert torch.equal(first, torch.zeros_like(first)), "현재 write를 같은 step에서 읽은 미래 누출"
    second, weights, _state2 = memory.step(key_a, key_b, value_b, state1)
    assert second[0] > 2.9 and int(weights.argmax()) == 0

    prefix1, _ = rollout(memory, [(key_a, value_a), (key_a, value_b)])
    prefix2, _ = rollout(memory, [(key_a, value_a), (key_a, -value_b)])
    assert torch.equal(prefix1[0], prefix2[0])
    assert torch.equal(prefix1[1], prefix2[1]), "미래 write가 prefix 출력에 영향"

    changed, _ = rollout(memory, [(key_a, -value_a), (key_a, value_b)])
    assert not torch.equal(prefix1[1], changed[1]), "과거 memory 내용에 출력이 의존하지 않음"

    # 작은 fp32 fixture로 functional write의 autograd graph가 유한한지 확인한다.
    grad_memory = CausalScoutMemory(slots=4, key_dim=2, value_dim=3, dtype=torch.float32)
    k = torch.tensor([2.0, 0.0], requires_grad=True)
    v = torch.tensor([1.0, 2.0, 3.0], requires_grad=True)
    s = grad_memory.empty()
    _r0, _w0, s = grad_memory.step(k, k, v, s)
    r1, _w1, _s = grad_memory.step(k, k, v * 0.5, s)
    r1.sum().backward()
    assert k.grad is not None and v.grad is not None
    assert torch.isfinite(k.grad).all() and torch.isfinite(v.grad).all()

    print("[PASS] P095 S0: read-before-write, prefix invariance, history dependence, 1 MiB, backward")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
