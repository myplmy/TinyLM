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

class WindowBoundaryTable:
    """Synthetic fixed-window boundary index; no model/file/large-cache creation.

    A token ID alone is not a Transformer activation key: left context and RoPE
    position must match. This table only accepts the exact pinned full window.
    The caller must separately verify that `hidden` came from `parent_sha256`.
    """

    POLICY = "fixed_window_causal_start0_v1"

    def __init__(self, tokens: torch.Tensor, hidden: torch.Tensor, *,
                 parent_sha256: str, split_layer: int, quantized: bool, group: int = 64,
                 context_policy: str = POLICY):
        import hashlib
        import re
        if (tokens.ndim != 2 or tokens.dtype != torch.long or tokens.shape[1] < 2
                or hidden.ndim != 3 or hidden.shape[:2] != tokens.shape
                or not re.fullmatch(r"[0-9A-Fa-f]{64}", parent_sha256)
                or not isinstance(split_layer, int) or split_layer < 1
                or context_policy != self.POLICY):
            raise ValueError("X3 requires pinned full causal windows, parent and split")
        self.windows, self.seq, self.dim = hidden.shape
        self.parent_sha256 = parent_sha256.upper()
        self.split_layer = split_layer
        self.context_policy = context_policy
        rows = tokens.detach().to("cpu").contiguous()
        self.window_hashes = tuple(hashlib.sha256(row.numpy().tobytes()).hexdigest()
                                   for row in rows)
        self.table = BoundaryTable(hidden.reshape(-1, self.dim),
                                   quantized=quantized, group=group)

    @property
    def payload_bytes(self) -> int:
        return self.table.payload_bytes

    def gather(self, window_ids: torch.Tensor, tokens: torch.Tensor, *,
               parent_sha256: str, split_layer: int, context_policy: str = POLICY,
               device=None) -> torch.Tensor:
        import hashlib
        if (parent_sha256.upper() != self.parent_sha256
                or split_layer != self.split_layer or context_policy != self.context_policy
                or window_ids.ndim != 1 or window_ids.dtype != torch.long
                or tokens.ndim != 2 or tokens.dtype != torch.long
                or tokens.shape != (window_ids.numel(), self.seq)):
            raise ValueError("X3 frozen-window provenance/shape differs")
        ids = window_ids.detach().to("cpu")
        rows = tokens.detach().to("cpu").contiguous()
        for index, row in zip(ids.tolist(), rows):
            if not 0 <= index < self.windows:
                raise IndexError("X3 window index outside cache")
            if hashlib.sha256(row.numpy().tobytes()).hexdigest() != self.window_hashes[index]:
                raise ValueError("X3 same token ID has different window context or order")
        flat = (ids[:, None] * self.seq + torch.arange(self.seq)).reshape(-1)
        return self.table.gather(flat, device=device).reshape(ids.numel(), self.seq, self.dim)

def fixed_window_starts(token_count: int, seq: int) -> torch.Tensor:
    """Nonoverlapping S+1 NTP windows; no random crop or document reinterpretation."""
    if not isinstance(token_count, int) or not isinstance(seq, int) or seq < 2 or token_count <= seq:
        raise ValueError("X3 fixed window needs integer token_count > seq >= 2")
    return torch.arange(0, token_count - seq, seq, dtype=torch.long)


def gather_fixed_window_xy(stream: torch.Tensor, starts: torch.Tensor, seq: int):
    """Return exact x/y crops; reject any off-grid or out-of-range start."""
    if (stream.ndim != 1 or stream.dtype != torch.long or starts.ndim != 1
            or starts.dtype != torch.long or not isinstance(seq, int) or seq < 2):
        raise ValueError("X3 fixed window stream/starts must be 1D integer tensors")
    ids = starts.detach().to("cpu")
    if ids.numel() and (bool((ids < 0).any()) or bool((ids % seq != 0).any())
                         or int(ids.max()) + seq >= stream.numel()):
        raise ValueError("X3 random/off-grid crop cannot reuse fixed-window cache")
    offsets = torch.arange(seq + 1, device=stream.device)
    raw = stream[(starts.to(stream.device)[:, None] + offsets[None, :])]
    return raw[:, :-1], raw[:, 1:]

def ffn_tile_accounting(dim: int, ffn_dim: int, layers: int, tile_size: int, active_tiles: int) -> dict:
    """X2 operand reduction vs unchanged dense Muon state; no speed claim."""
    if (min(dim, ffn_dim, layers, tile_size, active_tiles) < 1
            or ffn_dim % tile_size or active_tiles > ffn_dim // tile_size):
        raise ValueError("invalid X2 FFN tile accounting dimensions")
    full = layers * 3 * dim * ffn_dim
    selected = layers * 3 * dim * tile_size * active_tiles
    return {"full_ffn_weight_elements": full,
            "selected_gemm_weight_elements": selected,
            "selected_operand_fraction": selected / full,
            "fp32_master_bytes": full * 4,
            "muon_buffer_bytes": full * 4,
            "optimizer_shape_fraction": 1.0}

def fixed_window_cache_budget(source_tokens: int, seq: int, dim: int, *,
                              group: int = 64, exact_dtype_bytes: int = 4) -> dict:
    """Lower-bound payload sizes for aligned S+1 crops; no allocation or speed claim."""
    values = (source_tokens, seq, dim, group, exact_dtype_bytes)
    if (any(isinstance(value, bool) or not isinstance(value, int) for value in values)
            or source_tokens <= seq or seq < 2 or dim < 1 or group < 1
            or dim % group or exact_dtype_bytes not in (2, 4)):
        raise ValueError("invalid fixed-window cache layout")
    windows = (source_tokens - 1) // seq
    positions = windows * seq
    return {"windows": windows, "boundary_tokens": positions,
            "unused_source_tokens": source_tokens - positions - 1,
            "exact_payload_bytes": positions * dim * exact_dtype_bytes,
            "int8_per64_payload_bytes": boundary_cache_bytes(positions, dim, group=group),
            "window_hash_bytes": windows * 32, "window_offset_bytes": windows * 8}


def validate_window_cache_manifest(manifest: dict) -> dict:
    """Validate a proposed pinned layout, not the existence or contents of a cache file."""
    import re
    if not isinstance(manifest, dict) or manifest.get("schema") != "P103A_FIXED_WINDOW_CACHE_V1":
        raise ValueError("unknown fixed-window manifest")
    hashes = ("parent_sha256", "tokenizer_sha256", "source_cache_meta_sha256",
              "source_window_sha256", "lower_function_sha256")
    if any(not isinstance(manifest.get(key), str) or not re.fullmatch(
            "[0-9A-Fa-f]{64}", manifest[key]) for key in hashes):
        raise ValueError("fixed-window cache provenance hash is missing")
    if (manifest.get("context_policy") != "fixed_window_causal_start0_v1"
            or manifest.get("tokenizer_lineage") != "legacy32"
            or not isinstance(manifest.get("backend_signature"), str)
            or not manifest["backend_signature"].strip()
            or not isinstance(manifest.get("split_layer"), int)
            or isinstance(manifest["split_layer"], bool) or manifest["split_layer"] < 1):
        raise ValueError("fixed-window model/position contract differs")
    precision = manifest.get("precision")
    if precision not in ("fp32", "bf16", "fp16", "int8_per64"):
        raise ValueError("unsupported fixed-window precision")
    layout = fixed_window_cache_budget(
        manifest.get("source_tokens"), manifest.get("seq"), manifest.get("dim"),
        group=manifest.get("group", 64),
        exact_dtype_bytes=4 if precision == "fp32" else 2)
    required_bytes = (layout["int8_per64_payload_bytes"] if precision == "int8_per64"
                      else layout["exact_payload_bytes"])
    if (manifest.get("windows") != layout["windows"]
            or manifest.get("boundary_tokens") != layout["boundary_tokens"]
            or manifest.get("payload_bytes") != required_bytes):
        raise ValueError("fixed-window cache shape or byte count differs")
    return layout
