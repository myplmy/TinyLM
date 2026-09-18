"""P093 GPU-free accounting for direct and relaxed layer sharing candidates."""
from __future__ import annotations

from dataclasses import dataclass
import math


TERNARY_CODE_BITS = math.log2(3.0)
SCALE_BITS = 16.0


def _packed_matrix_bytes(out_features: int, in_features: int, group: int) -> float:
    effective_group = (
        group if group and in_features % group == 0 else in_features
    )
    bits = out_features * in_features * TERNARY_CODE_BITS
    bits += out_features * (in_features // effective_group) * SCALE_BITS
    return bits / 8.0


def _mlp_shapes(dim: int, width: int):
    return ((width, dim), (width, dim), (dim, width))


def _lora_shapes(dim: int, width: int, rank: int):
    # gate/up/down each own D and U.
    return (
        (rank, dim), (width, rank),
        (rank, dim), (width, rank),
        (rank, width), (dim, rank),
    )


@dataclass(frozen=True)
class SharingCandidate:
    candidate_id: str
    middle_unique: int
    middle_width: int
    residual_rank: int = 0
    logical_middle_visits: int = 16


@dataclass(frozen=True)
class SharingAccount:
    candidate_id: str
    unique_matrix_params: int
    packed_bytes: float
    train_resident_lower_bound_bytes: int
    linear_flops_per_token: int
    deployment_saving_ratio: float
    extra_flops_ratio: float
    optimizer_state_bytes: int
    metadata_bytes: int


def _common_shapes(cfg):
    dim = cfg.dim
    shapes = []
    # q/o at every logical layer; k/v only at CLA owners.
    shapes.extend([(dim, dim), (dim, dim)] * cfg.n_layers)
    kv_owners = sum(1 for i in range(cfg.n_layers) if i - (i % cfg.cla_group) == i)
    shapes.extend([(cfg.kv_dim, dim), (cfg.kv_dim, dim)] * kv_owners)
    return shapes


def _candidate_shapes(cfg, candidate: SharingCandidate):
    shapes = list(_common_shapes(cfg))
    edge_modules = cfg.n_prelude + cfg.n_coda
    for _ in range(edge_modules):
        shapes.extend(_mlp_shapes(cfg.dim, cfg.ffn_dim))
    for _ in range(candidate.middle_unique):
        shapes.extend(_mlp_shapes(cfg.dim, candidate.middle_width))
    if candidate.residual_rank:
        for _ in range(candidate.logical_middle_visits):
            shapes.extend(_lora_shapes(cfg.dim, candidate.middle_width, candidate.residual_rank))
    return shapes


def _packed_total(cfg, shapes):
    packed = sum(_packed_matrix_bytes(o, i, cfg.micro_group) for o, i in shapes)
    emb_dim = cfg.emb_rank if cfg.emb_rank else cfg.dim
    if cfg.quantize_embedding:
        packed += _packed_matrix_bytes(cfg.vocab_size, emb_dim, cfg.micro_group)
    else:
        packed += cfg.vocab_size * emb_dim * 4
    if cfg.emb_rank:
        packed += cfg.dim * emb_dim * 4
    # Layer scales/shifts/gates and final scale stay full precision.
    packed += (cfg.n_layers * (4 * cfg.dim + 2) + cfg.dim) * 4
    return packed


def account_candidate(cfg, candidate: SharingCandidate, dense_reference=None) -> SharingAccount:
    shapes = _candidate_shapes(cfg, candidate)
    matrix_params = sum(o * i for o, i in shapes)
    emb_dim = cfg.emb_rank if cfg.emb_rank else cfg.dim
    embedding_table_params = cfg.vocab_size * emb_dim
    embedding_projection_params = cfg.dim * emb_dim if cfg.emb_rank else 0
    embedding_params = embedding_table_params + embedding_projection_params
    small_params = cfg.n_layers * (4 * cfg.dim + 2) + cfg.dim
    total_params = matrix_params + embedding_params + small_params

    # Muon matrix state is one full-size momentum buffer. Embedding/small values
    # use AdamW's two moments. Parameters and gradients are fp32 in this model.
    # split_params() excludes only nn.Embedding from Muon; a low-rank emb_up
    # projection is still a 2-D Muon matrix and owns one momentum buffer.
    optimizer_state = (
        (matrix_params + embedding_projection_params) * 4
        + (embedding_table_params + small_params) * 8
    )
    train_resident = total_params * 8 + optimizer_state

    attention_flops = 2 * sum(o * i for o, i in _common_shapes(cfg))
    edge_visits = cfg.n_prelude + cfg.n_coda
    mlp_flops = 2 * 3 * cfg.dim * (
        edge_visits * cfg.ffn_dim
        + candidate.logical_middle_visits * candidate.middle_width
    )
    residual_flops = 0
    if candidate.residual_rank:
        residual_flops = 2 * candidate.logical_middle_visits * sum(
            o * i for o, i in _lora_shapes(cfg.dim, candidate.middle_width, candidate.residual_rank)
        )
    linear_flops = attention_flops + mlp_flops + residual_flops
    packed = _packed_total(cfg, shapes)
    metadata = len(shapes) * 16

    if dense_reference is None:
        saving = 0.0
        extra_flops = 0.0
    else:
        saving = 1.0 - packed / dense_reference.packed_bytes
        extra_flops = linear_flops / dense_reference.linear_flops_per_token - 1.0
    return SharingAccount(
        candidate.candidate_id,
        matrix_params,
        packed,
        train_resident,
        linear_flops,
        saving,
        extra_flops,
        optimizer_state,
        metadata,
    )


def standard_candidates(cfg):
    dense = SharingCandidate("dense", cfg.n_middle, cfg.ffn_dim)
    rows = [
        dense,
        SharingCandidate("E0-g2", cfg.n_middle // 2, cfg.ffn_dim),
        SharingCandidate("D1-wide-core", cfg.n_middle // 4, cfg.ffn_dim * 2),
        SharingCandidate("D2-use-normalized", cfg.n_middle // 2, cfg.ffn_dim),
        SharingCandidate("D3-cycle", cfg.n_middle // 2, cfg.ffn_dim),
    ]
    rows.extend(
        SharingCandidate(f"R1-depth-lowrank-r{rank}", cfg.n_middle // 2, cfg.ffn_dim, rank)
        for rank in (4, 8, 16)
    )
    return rows
