"""아키텍처 설정의 단일 소스.

새 아키텍처 실험은 이 파일의 PRESETS 만 바꾸면 된다 — 모델/데이터/학습 코드는 재사용.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

VOCAB = 32768


@dataclass
class TMTConfig:
    # --- shape ---
    vocab_size: int = 32768
    dim: int = 768
    ffn_dim: int = 2048
    n_q_heads: int = 12
    n_kv_heads: int = 3               # GQA
    emb_rank: int = 256               # factorized embedding 병목. 0이면 비활성

    # --- depth / tying ---
    n_prelude: int = 2                # 완전 독립
    n_middle: int = 16                # 어텐션 독립 + MLP 타잉
    n_coda: int = 2                   # 완전 독립
    mlp_group: int = 4                # 중간층 MLP를 몇 층씩 묶을지
    cla_group: int = 2                # K/V를 몇 층이 공유할지 (1이면 비활성)

    # --- mode control ---
    n_modes: int = 1
    mode_rank: int = 0

    # --- ternary ---
    micro_group: int = 128
    twn_thr_ratio: float = 0.7
    ste_clip: float = 2.5
    quant_anneal: float = 1.0
    quantize_embedding: bool = True

    # --- relaxation: RRT식 층별 LoRA (공유 MLP 위, 배포 메모리 최소) ---
    mlp_lora_rank: int = 0            # 0이면 비활성
    mlp_lora_bits: int = 2           # 2=삼진(저비트), 16=fp16
    mlp_film: bool = False           # 층별 FiLM(공유 MLP 은닉 변조, 거의 공짜)

    # --- misc ---
    max_seq_len: int = 2048
    rope_theta: float = 10000.0
    norm_eps: float = 1e-5
    grad_checkpoint: bool = False
    tie_mlp: bool = True              # False면 dense 기준선

    def __post_init__(self):
        assert self.dim % self.n_q_heads == 0
        assert self.n_q_heads % self.n_kv_heads == 0
        assert self.dim % self.micro_group == 0 and self.ffn_dim % self.micro_group == 0
        assert self.n_middle % self.mlp_group == 0

    @property
    def head_dim(self): return self.dim // self.n_q_heads
    @property
    def kv_dim(self): return self.n_kv_heads * self.head_dim
    @property
    def n_layers(self): return self.n_prelude + self.n_middle + self.n_coda
    @property
    def n_mlp_groups(self): return self.n_middle // self.mlp_group if self.tie_mlp else self.n_middle


def dense_baseline(cfg: TMTConfig) -> TMTConfig:
    """동일 shape·동일 토큰 예산으로 학습할 기준선. 타잉과 CLA만 끈다."""
    return dataclasses.replace(cfg, tie_mlp=False, cla_group=1)


# ---------------------------------------------------------------------------
# 프리셋: 이름 -> (seq, ckpt) -> TMTConfig(tied 기준). dense는 build_config 에서 파생.
# ---------------------------------------------------------------------------

def _tiny(seq, ckpt):
    return TMTConfig(vocab_size=VOCAB, dim=256, ffn_dim=512, n_q_heads=4, n_kv_heads=1,
                     emb_rank=64, n_prelude=1, n_middle=4, n_coda=1,
                     mlp_group=2, cla_group=2, n_modes=1, mode_rank=0,
                     micro_group=128, max_seq_len=seq, grad_checkpoint=ckpt)


def _m100(seq, ckpt):
    return TMTConfig(vocab_size=VOCAB, dim=768, ffn_dim=2048, n_q_heads=12, n_kv_heads=3,
                     emb_rank=256, n_prelude=2, n_middle=16, n_coda=2,
                     mlp_group=4, cla_group=2, n_modes=1, mode_rank=0,
                     micro_group=128, max_seq_len=seq, grad_checkpoint=ckpt)


def _m100d(seq, ckpt):   # 깊고 얇게: 중간층 24, g6 (MLP 그룹 4개는 동일, 깊이만 증가)
    return TMTConfig(vocab_size=VOCAB, dim=768, ffn_dim=2048, n_q_heads=12, n_kv_heads=3,
                     emb_rank=256, n_prelude=2, n_middle=24, n_coda=2,
                     mlp_group=6, cla_group=2, n_modes=1, mode_rank=0,
                     micro_group=128, max_seq_len=seq, grad_checkpoint=ckpt)


PRESETS = {"tiny": _tiny, "m100": _m100, "m100d": _m100d}


def build_config(preset: str, arch: str, seq: int, ckpt: bool = True) -> TMTConfig:
    if preset not in PRESETS:
        raise KeyError(f"unknown preset {preset!r}; 있는 것: {list(PRESETS)}")
    cfg = PRESETS[preset](seq, ckpt)
    return cfg if arch == "tied" else dense_baseline(cfg)
