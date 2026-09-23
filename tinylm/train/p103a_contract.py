"""P103A opt-in tensor contracts for FFN tiles and fixed-prefix INT8 cache."""
from __future__ import annotations

import torch
import torch.nn.functional as F


def ffn_tiles(x, gate, up, down, active_tiles, *, tile_size=512):
    """Physically slice SwiGLU channels, preserving full-width output shape."""
    width = gate.shape[0]
    if up.shape != gate.shape or down.shape[1] != width or tile_size < 1 or width % tile_size:
        raise ValueError("FFN tile shapes are incompatible")
    total = width // tile_size
    chosen = sorted(set(active_tiles))
    if not chosen or any(not 0 <= i < total for i in chosen):
        raise ValueError("active tiles outside FFN width")
    indices = torch.cat([torch.arange(i * tile_size, (i + 1) * tile_size,
                                     device=x.device) for i in chosen])
    hidden = F.silu(F.linear(x, gate.index_select(0, indices))) * F.linear(
        x, up.index_select(0, indices))
    out = F.linear(hidden, down.index_select(1, indices))
    return out * (total / len(chosen))


def quantize_boundary_int8(x, *, group=64):
    """Per-token, per-channel-group symmetric INT8 cache values and FP32 scales."""
    if x.ndim != 2 or group < 1 or x.shape[1] % group:
        raise ValueError("boundary must be [tokens,dim] with divisible group")
    if not bool(torch.isfinite(x).all()):
        raise ValueError("non-finite boundary activation")
    chunks = x.float().reshape(x.shape[0], x.shape[1] // group, group)
    scales = chunks.abs().amax(dim=-1).clamp_min(1e-12) / 127.0
    codes = torch.round(chunks / scales[..., None]).clamp(-127, 127).to(torch.int8)
    return codes.reshape_as(x).contiguous(), scales.contiguous()


def dequantize_boundary_int8(codes, scales, *, group=64):
    if codes.dtype != torch.int8 or codes.ndim != 2 or group < 1 or codes.shape[1] % group:
        raise ValueError("invalid INT8 boundary codes")
    if scales.shape != (codes.shape[0], codes.shape[1] // group):
        raise ValueError("boundary scale shape mismatch")
    return (codes.float().reshape(codes.shape[0], -1, group)
            * scales.float()[..., None]).reshape(codes.shape)


def boundary_cache_bytes(tokens, dim, *, group=64, scale_bytes=4):
    if min(tokens, dim, group, scale_bytes) < 1 or dim % group:
        raise ValueError("invalid cache dimensions")
    return tokens * (dim + (dim // group) * scale_bytes)


class BoundaryTable:
    """CPU-only frozen-prefix boundary table; no file or protected-data I/O."""

    def __init__(self, hidden: torch.Tensor, *, quantized: bool, group: int = 64):
        if (group < 1 or hidden.ndim != 2 or min(hidden.shape) < 1
                or hidden.shape[1] % group or not bool(torch.isfinite(hidden).all())):
            raise ValueError("boundary table requires nonempty [tokens,dim] and divisible group")
        source = hidden.detach().to("cpu").contiguous()
        self.shape = tuple(source.shape)
        self.group = group
        self.quantized = bool(quantized)
        self.values = self.codes = self.scales = None
        if self.quantized:
            self.codes, self.scales = quantize_boundary_int8(source, group=group)
        else:
            self.values = source.clone()

    @property
    def payload_bytes(self) -> int:
        if self.quantized:
            return self.codes.numel() * self.codes.element_size() + (
                self.scales.numel() * self.scales.element_size())
        return self.values.numel() * self.values.element_size()

    def gather(self, indices: torch.Tensor, *, device=None) -> torch.Tensor:
        if indices.ndim != 1 or indices.dtype != torch.long:
            raise ValueError("boundary indices must be a 1D long tensor")
        ids = indices.detach().to("cpu")
        if ids.numel() and (int(ids.min()) < 0 or int(ids.max()) >= self.shape[0]):
            raise IndexError("boundary index outside frozen source")
        if self.quantized:
            result = dequantize_boundary_int8(
                self.codes.index_select(0, ids),
                self.scales.index_select(0, ids), group=self.group)
        else:
            result = self.values.index_select(0, ids)
        return result.to(device) if device is not None else result
