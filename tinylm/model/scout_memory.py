"""P095 S0용 causal Scout/LTM primitive.

이 모듈은 Transformer에 연결되지 않는다. 현재 step의 write보다 과거 state를 먼저 읽는
read-before-write 계약과 논리 payload 회계를 독립적으로 검증하기 위한 최소 구현이다.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class ScoutMemoryState:
    keys: torch.Tensor
    values: torch.Tensor
    valid: torch.Tensor
    cursor: torch.Tensor


class CausalScoutMemory(torch.nn.Module):
    """고정 slot exact-scan 메모리. metadata는 1 MiB payload와 별도다."""

    def __init__(self, slots=1024, key_dim=128, value_dim=384, dtype=torch.bfloat16):
        super().__init__()
        if min(slots, key_dim, value_dim) < 1:
            raise ValueError("slots/key_dim/value_dim은 양수여야 한다")
        self.slots = int(slots)
        self.key_dim = int(key_dim)
        self.value_dim = int(value_dim)
        self.dtype = dtype

    @property
    def logical_payload_bytes(self) -> int:
        return self.slots * (self.key_dim + self.value_dim) * torch.empty((), dtype=self.dtype).element_size()

    def empty(self, *, device=None) -> ScoutMemoryState:
        return ScoutMemoryState(
            keys=torch.zeros(self.slots, self.key_dim, dtype=self.dtype, device=device),
            values=torch.zeros(self.slots, self.value_dim, dtype=self.dtype, device=device),
            valid=torch.zeros(self.slots, dtype=torch.bool, device=device),
            cursor=torch.zeros((), dtype=torch.long, device=device),
        )

    def read(self, query: torch.Tensor, state: ScoutMemoryState):
        if query.shape != (self.key_dim,):
            raise ValueError(f"query shape {tuple(query.shape)} != {(self.key_dim,)}")
        if not bool(state.valid.any()):
            # 계산 그래프를 보존하되 빈 memory는 정확히 0을 반환한다.
            zero = state.values.sum(dim=0) * 0 + query.sum() * 0
            return zero.to(query.dtype), torch.zeros(self.slots, dtype=query.dtype, device=query.device)
        scores = state.keys.to(query.dtype).matmul(query) / math.sqrt(self.key_dim)
        scores = scores.masked_fill(~state.valid, torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores, dim=0)
        value = weights.matmul(state.values.to(query.dtype))
        return value, weights

    def write(self, key: torch.Tensor, value: torch.Tensor,
              state: ScoutMemoryState) -> ScoutMemoryState:
        if key.shape != (self.key_dim,) or value.shape != (self.value_dim,):
            raise ValueError("write key/value shape 불일치")
        index = torch.remainder(state.cursor, self.slots)
        mask = F.one_hot(index, num_classes=self.slots).to(key.dtype).unsqueeze(1)
        keys = state.keys.to(key.dtype) * (1 - mask) + key.unsqueeze(0) * mask
        vmask = mask.to(value.dtype)
        values = state.values.to(value.dtype) * (1 - vmask) + value.unsqueeze(0) * vmask
        valid = state.valid | F.one_hot(index, num_classes=self.slots).to(torch.bool)
        return ScoutMemoryState(keys.to(self.dtype), values.to(self.dtype), valid, state.cursor + 1)

    def step(self, query: torch.Tensor, write_key: torch.Tensor, write_value: torch.Tensor,
             state: ScoutMemoryState, *, enable_write=True):
        """과거 state를 읽은 뒤에만 현재 정보를 쓴다."""
        read_value, weights = self.read(query, state)
        next_state = self.write(write_key, write_value, state) if enable_write else state
        return read_value, weights, next_state


class ScoutMemoryBridge(torch.nn.Module):
    """Default-off hidden-state bridge for the P095 S0b integration contract.

    It deliberately supports one sequence at a time.  Full batched Transformer
    wiring, retrieval supervision and learned write policy remain later gates.
    """

    def __init__(self, hidden_dim: int, memory: CausalScoutMemory):
        super().__init__()
        self.hidden_dim = int(hidden_dim)
        self.memory = memory
        self.query = torch.nn.Linear(hidden_dim, memory.key_dim, bias=False)
        self.write_key = torch.nn.Linear(hidden_dim, memory.key_dim, bias=False)
        self.write_value = torch.nn.Linear(hidden_dim, memory.value_dim, bias=False)
        self.fuse = torch.nn.Linear(memory.value_dim, hidden_dim, bias=False)
        self.gate = torch.nn.Parameter(torch.zeros(()))

    @staticmethod
    def state_bytes(state: ScoutMemoryState) -> int:
        return sum(
            tensor.numel() * tensor.element_size()
            for tensor in (state.keys, state.values, state.valid, state.cursor)
        )

    def forward(self, hidden: torch.Tensor, state: ScoutMemoryState,
                write_mask: torch.Tensor | None = None):
        if hidden.ndim != 2 or hidden.shape[1] != self.hidden_dim:
            raise ValueError(f"hidden must be [T,{self.hidden_dim}], got {tuple(hidden.shape)}")
        if write_mask is None:
            write_mask = torch.ones(hidden.shape[0], dtype=torch.bool, device=hidden.device)
        if write_mask.shape != (hidden.shape[0],):
            raise ValueError("write_mask must have shape [T]")
        outputs = []
        current = state
        for index, vector in enumerate(hidden):
            read, _weights, current = self.memory.step(
                self.query(vector), self.write_key(vector), self.write_value(vector), current,
                enable_write=bool(write_mask[index]),
            )
            outputs.append(vector + self.gate * self.fuse(read))
        return torch.stack(outputs), current
