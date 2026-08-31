"""아키텍처 설정의 단일 소스.

새 아키텍처 실험은 이 파일의 PRESETS 만 바꾸면 된다 — 모델/데이터/학습 코드는 재사용.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

VOCAB = 32768

# ★★2026-08-22 실사고(함정 18: 적용 대상 집합을 두 곳에서 정의) — **여기가 유일한 정본이다.**
#
#   `--repeat-mode inplace` 를 신설하면서 **`cli.py` 의 choices 와 `transformer._repeat_schedule`
#   에만 넣고 아래 `__post_init__` 의 assert 를 안 고쳤다.**
#   ★**학습은 통과했다** — `build_config` 가 만든 뒤 `trainer` 가 필드를 **대입**하므로
#   `__post_init__` 이 다시 안 돌기 때문이다.
#   🚫**죽은 것은 평가였다**: `load_model` 이 `TMTConfig(**st["cfg"])` 로 **재구성**하면서
#   assert 가 터졌다. **2.8시간 학습이 끝난 뒤에.**
#   → ★**목록을 한 곳에 두고 세 경로가 전부 이것을 import 한다.**
REPEAT_MODES = ("uniform", "block", "progressive", "inplace")


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
    # ★P061(2026-08-13) — **불균등 타잉.** 균등 `mlp_group` 대신 **경계 목록**을 준다.
    #   비어 있으면 종전 균등 = **비트 동일.**  `(12,)` → [0..11][12..15] / `(4,)` → [0..3][4..15]
    #   ★유니크 MLP 개수(=len(split)+1)를 기준선과 같게 두면 **메모리가 완전히 동일**하고
    #     "층의 역할이 다른가" 만 남는다. 그게 이 축의 설계 의도다.
    mlp_split: tuple = ()
    cla_group: int = 2                # K/V를 몇 층이 공유할지 (1이면 비활성)
    # ★P057(2026-08-13) — **어텐션 타잉.** 중간층 g 개가 어텐션 하나를 공유한다.
    #   1 = 층마다 독립 = 종전 = **비트 동일**. 삼진의 48.4% 가 어텐션인데 한 번도 안 묶었다.
    attn_group: int = 1
    # ★P049B(2026-08-13) — **학습 시 재귀.** 중간 블록을 몇 배로 통과할지.
    #   1.0 = 종전 = 비트 동일. `infer_repeat`(P031, 추론 전용)과 **다른 축**이다 —
    #   이쪽은 backward 를 통과하므로 학습 분포 자체가 반복을 본다.
    train_repeat: float = 1.0
    repeat_mode: str = "uniform"      # uniform=중간 전체 / block=특정 그룹만 / progressive=깊을수록 증가
    repeat_block: int = 0             # block 모드에서 반복할 MLP 그룹 인덱스

    # --- mode control ---
    n_modes: int = 1
    mode_rank: int = 0

    # --- ternary ---
    micro_group: int = 128            # ★0 = per-row 센티널(그룹 = in_f 전체). P014C 단계2/3
    twn_thr_ratio: float = 0.7
    ste_clip: float = 2.5
    quant_anneal: float = 1.0
    quantize_embedding: bool = True
    # ★P034 단계5(2026-08-22) — 임베딩 양자화. **배포 전용**이고 학습에는 영향이 없다.
    #   `emb_chunk` 는 헤드 GEMM 을 어휘 축으로 자르는 크기(0 = 끄기).
    #   4096 이면 동시 fp32 버퍼가 `4096 x E x 4B` = 4 MiB(E=256) 로 묶인다.
    emb_chunk: int = 0
    # ★P068 A1(2026-08-22) — `_wq` **저장** dtype. 계산은 fp32 로 하고 저장만 내린다.
    #   기본 fp32 = 비트 동일. bf16 이면 `F.linear` 진입 캐스팅이 사라진다(결과 035 §13).
    wq_dtype: str = "fp32"
    sparse34: bool = False            # (P016) 3:4 희소 삼진(4개마다 |w|최소 1개 0강제) = 1.25bpw

    # --- relaxation: RRT식 층별 LoRA (공유 MLP 위, 배포 메모리 최소) ---
    mlp_lora_rank: int = 0            # 0이면 비활성
    mlp_lora_bits: int = 2           # 2=삼진(저비트), 16=fp16
    mlp_film: bool = False           # 층별 FiLM(공유 MLP 은닉 변조, 거의 공짜)
    attn_kind: str = "softmax_cla"   # 어텐션 종류(컴포넌트 선택). 신규는 register_attention 로 등록
    # ── F-1 (2026-08-14) : GQA 를 SDPA 에 맡긴다 ──────────────────────────────
    #   기본 False = **종전 `repeat_interleave` 경로 = 비트 동일**. True 면 K/V 를 물리적으로
    #   n_rep 배 복제하지 않고 `enable_gqa=True` 로 커널에 넘긴다(활성 메모리 절감).
    #   ⚠️ 커널 경로가 달라지므로 **로짓이 비트 동일하지 않을 수 있다** — 게이트가 잰다.
    sdpa_gqa: bool = False
    # ── P014C 단계2 (2026-08-14) : per-row 융합 int8 matmul ────────────────────
    #   기본 False = 종전 경로. True 면 `_i8` 저장 + **per-row α**(micro_group=0) 일 때만
    #   `torch._weight_int8pack_mm` 로 **fp32 복원 없이** 곱한다. 조건 미충족이면 조용히
    #   종전 경로로 떨어지지 **않고** 크게 알린다(조용한 무동작 금지).
    fused_int8: bool = False
    center_weights: bool = False     # (실험) g128 그룹별 latent weight mean-centering
    use_ternary_kernel: bool = False # (실험) 커스텀 삼진 커널 경로 사용(기본 off = 기존 경로)
    ternary_kernel_triton: bool = False  # 커널 내부에서 Triton forward(검증 후에만 True)

    # --- misc ---
    max_seq_len: int = 2048
    rope_theta: float = 10000.0
    norm_eps: float = 1e-5
    grad_checkpoint: bool = False
    tie_mlp: bool = True              # False면 dense 기준선

    # ── P031 단계0 : 추론 시 middle 블록 반복(깊이 외삽). **추론 전용, 학습 경로 무영향** ──
    #   infer_repeat = middle 층 통과 횟수의 배수. 1.0 이면 학습된 그대로(기본).
    #     0.5 → 16층 중 8층만 통과(축소·지연 절감) / 1.5 → 24회 통과(확장)
    #   repeat_where = 분수 R 에서 **어디를** 더 돌리거나 건너뛸지. 결과가 이것에 의존하므로
    #     한 배치만 보고 일반화하지 않는다(계획 P031 §설계).
    #   repeat_kv_reuse = 반복 통과에서 CLA owner 의 KV 를 재계산하지 않고 첫 통과 것을 재사용.
    #     기본 False(재계산) — '층이 늘어난 것'의 충실한 유추는 재계산 쪽이다.
    infer_repeat: float = 1.0
    repeat_where: str = "front"       # front | back | even
    repeat_kv_reuse: bool = False
    # ★★P077 단계1 (2026-08-30) — **KV 캐시 저장 정밀도.**
    #   결과 062 가 `repeat_kv_reuse` 를 기각하면서 **엔트리 수를 줄이는 길이 닫혔다.**
    #   남은 KV 레버는 **엔트리당 바이트**뿐이다. bf16 이면 정확히 절반.
    #   ⚠️저장만 낮추고 **계산은 fp32 로 되올린다** — 활성값·산술은 어느 모드에서도 같다.
    #   기본 fp32 = 캐스팅을 건너뛰므로 **종전 경로와 비트 동일**.
    kv_dtype: str = "fp32"            # fp32 | bf16 | fp16
    # ★★P081 선결 (2026-08-31) — **어텐션 확률을 밖으로 낸다(진단 전용).**
    #   🚫SDPA 는 확률을 안 준다 → 어텐션 싱크(StreamingLLM)를 한 번도 못 봤다.
    #   켜면 `Attention.forward` 가 **위에서 이미 만든 q·k·mask 그대로** 확률을 한 번 더
    #   계산해 `self.last_probs` 에 둔다. ⚠️**출력 경로에 안 들어가므로 on 이어도 로짓은
    #   비트 동일**하고, 대가는 **메모리와 시간**뿐이다((B,H,q,kv) x 4B).
    #   🚫**학습에서는 켜지 않는다** — `Attention.forward` 가 `self.training` 이면 단언으로 막는다.
    return_probs: bool = False
    # ★★P049 §17.3 (2026-08-22 사용자 허가 6.5-1) — **재귀 통과에서 어텐션 출력을 재사용.**
    #   결과 041 §17: 복제층 어텐션 출력 **cos 0.9882** = 두 번째 통과가 거의 같은 것을
    #   다시 계산한다. 켜면 두 번째 이후 통과에서 **어텐션(그리고 소비자가 없으면 KV 계산까지)
    #   을 건너뛰고 첫 통과 출력을 그대로 쓴다.** ★**우리 축 중 연산이 실제로 주는 첫 레버.**
    #   ⚠️`infer_repeat`/`train_repeat` 이 1.0 이면 **죽은 코드 = 비트 동일**.
    #   ⚠️학습·추론 **양쪽에서 같은 값**을 써야 한다(함정 39).
    reuse_attn_on_dup: bool = False
    # ★★P014 단계1(2026-08-22) — LUT 배포 경로의 출력채널 청크.
    #   0 = 한 번에. gather 결과 `(B, J, O)` 가 크면 여기서 나눈다(수학적으로 동일).
    lut_out_chunk: int = 0

    # ── P036 단계0 : Arenas (Annealing Residual Synapse), arXiv:2601.07892 §3.2 ──
    #   Y = X·Tα + λ_t·X·W          (논문 식 7)
    #   ∂L/∂X = (∂L/∂Y)(Tα + λ_t·W)ᵀ (식 8)  ← latent W 가 **입력 gradient 경로**에 들어간다
    #   우리 어닐은 `(w - wq).detach()` 라 그 경로가 **없다**(결과 016 §8.6). 그래서 별도 항이다.
    #   λ_t 는 학습이 끝나면 0 → **추론 오버헤드 0**(배포 시 순수 삼진과 동일).
    #   ⚠️ 논문 ablation(Fig.6)은 3:4 뿐 아니라 **1-bit·1.67-bit 순수 삼진에도** 이득이라고 한다.
    arenas: bool = False
    arena_lambda: float = 0.1         # λ_0 — 학습 시작 시점의 residual 계수
    arena_end: float = 0.9            # 진행률 이 지점에서 λ_t = 0 (이후 순수 삼진)

    def __post_init__(self):
        assert self.dim % self.n_q_heads == 0
        assert self.n_q_heads % self.n_kv_heads == 0
        # ★micro_group == 0 은 **per-row 센티널**이다(그룹 = 층마다 다른 in_f).
        #   프리셋 필드 하나로 "층마다 다른 값" 을 표현할 수 없어서 0 을 약속어로 쓴다.
        #   P014C 단계3 §"선결 구현(소)". 0 이면 나눗셈 검사가 성립하지 않으므로 건너뛴다.
        if self.micro_group:
            assert self.dim % self.micro_group == 0 and self.ffn_dim % self.micro_group == 0
        assert self.n_middle % self.mlp_group == 0
        assert self.attn_group >= 1 and self.n_middle % self.attn_group == 0, \
            f"n_middle {self.n_middle} % attn_group {self.attn_group} != 0"
        assert self.train_repeat > 0, "train_repeat 는 양수여야 한다"
        assert self.repeat_mode in REPEAT_MODES, \
            f"repeat_mode 는 {'|'.join(REPEAT_MODES)} — 받은 값: {self.repeat_mode}"
        if self.sparse34:
            assert self.micro_group and self.micro_group % 4 == 0, \
                "sparse34 는 group 이 4의 배수여야 함(3:4 블록). per-row(0)와는 함께 못 쓴다"
        assert self.repeat_where in ("front", "back", "even"), \
            f"repeat_where 는 front|back|even — 받은 값: {self.repeat_where}"
        assert self.infer_repeat > 0, "infer_repeat 는 양수여야 한다"

    @property
    def head_dim(self): return self.dim // self.n_q_heads
    @property
    def kv_dim(self): return self.n_kv_heads * self.head_dim
    @property
    def n_layers(self): return self.n_prelude + self.n_middle + self.n_coda
    @property
    def n_mlp_groups(self):
        # ★P061: `mlp_split` 이 있으면 유니크 개수 = len(split)+1. 비면 종전 = 비트 동일.
        if not self.tie_mlp:
            return self.n_middle
        sp = tuple(getattr(self, "mlp_split", ()) or ())
        return (len(sp) + 1) if sp else (self.n_middle // self.mlp_group)


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


def _m100R1a(seq, ckpt):
    """★REVIEW1 후보 A — g4 + 3:4 준정형. **잠정 보존 승격**(2026-07-31 사용자 결정).

    `mA_g4s34_k4` 의 아키텍처를 프리셋으로 고정한 것. 학습 조합(KD k4·부모초기화)은
    프리셋이 아니라 **명령줄**(`--kd --init-from --kd-every 4`)이 정한다.

    ★왜 하나로 못 고르나: 품질 1.2σ / 저장 0.7% 차이 = **둘 다 노이즈 안**이고,
    A 의 우위는 **5비트 패킹 커널·Arenas 가 둘 다 미구현**인 것에 의존한다(결과 016 §7.6).
    → 승자 확정은 P034 단계2~4 · P036 이후. 그때까지 **둘 다 보존**한다.
    """
    return dataclasses.replace(_m100(seq, ckpt), mlp_group=4, sparse34=True)


def _m100R1c(seq, ckpt):
    """★REVIEW1 후보 C — g8, 3:4 없음. **잠정 보존 승격**(2026-07-31).

    `mC_g8_k4` 의 아키텍처. **상주 메모리 최소**(451.5MB vs A 523.5MB, 결과 016 §1)이고
    표준 경로만 쓰므로 **구현 리스크가 없다** → 현재 근거로는 **이쪽이 기본**이다.
    """
    return dataclasses.replace(_m100(seq, ckpt), mlp_group=8, sparse34=False)


# ★새 프리셋은 **기존 프리셋을 건드리지 않는다** — `_m100` 을 dataclasses.replace 로 파생만 한다.
#   체크포인트·로그 이름이 `{preset}_{data}_{tokens}_{tag}` 라 **네임스페이스가 자동 분리**되고,
#   기존 런(`m100_*`)과 충돌하지 않는다.
# ★프리셋 파생 관계(2026-08-01). `m100R1a/c` 는 `m100` 에서 한 필드만 바꾼 것이라
#   **부모 dense·KD 교사 체크포인트를 공유한다.** 이걸 명시하지 않아서 `--preset m100R1a
#   --init-from` 이 `m100R1a_..._dense.pt` 를 찾다 죽었다(P038·P036 단계2, 2026-08-01).
#   체크포인트 네임스페이스 분리는 의도한 것이고, 부모 탐색이 그걸 못 따라간 것이 버그였다.
PRESET_PARENT = {"m100R1a": "m100", "m100R1c": "m100", "m100d": "m100",
                 # ★P074 얕은 dense 4종 — 부모는 m100 dense(20층). **얕은 쪽 이식**이라
                 #   `--depth-init role` 이 필수다(init_utils §116).
                 "m100s2": "m100", "m100s4": "m100",
                 "m100s6": "m100", "m100s8": "m100", "m100s12": "m100",
                 "m100R1p": "m100", "m100R1q": "m100",
                 "m100R1d": "m100"}   # ★P048/P049: 부모는 m100 dense(20층) — 깊이가 달라 부분/확장 이식된다

def _m100R1p(seq, ckpt):
    """★P048 — `m100R1c`(g8) 에서 **prelude/coda 를 2+2 → 1+1** 로만 줄인 것.

    prelude·coda MLP 는 **타잉 대상이 아니라 층마다 독립**이다. 그래서 층 하나가
    유니크 MLP 하나를 통째로 쓴다 — 중간층은 8층이 하나를 나눠 쓰는데 말이다.
    유니크 MLP **6개 → 4개**(2+2+2 → 1+2+1) = **삼진 파라미터 −22.0%**.

    ⚠️ **깊이가 20 → 18 로 함께 줄어든다**(교락). `n_middle` 을 18 로 올려 깊이를
    유지하려면 `mlp_group` 이 18 을 나눠야 해서 g9 가 되고, 그러면 **부모 dense
    (`m100_*_dense.pt`, n_middle=16)에서 부모초기화·KD 가 불가능**하다
    (`mid_mlps[j*9+k]` 가 인덱스 17 을 찾는다). 계획 P048 §3.2 참조.
    → **깊이 교락을 안고 가는 대신 부모를 재사용한다**는 선택이다.

    ⚠️ 결과 002 는 "prelude/coda 2+2 가 단일 최대 이득" 이라 했으나 **그건 전층 타잉
    (prelude/coda 0+0) 대비**다. 1+1 은 그 사이 지점이고 **한 번도 측정하지 않았다.**
    """
    return dataclasses.replace(_m100R1c(seq, ckpt), n_prelude=1, n_coda=1)


def _m100R1q(seq, ckpt):
    """★P048 단계2 — `m100R1p`(prelude/coda 1+1) **+ g16**. 두 레버를 겹친 것.

    유니크 MLP **3개**(1 + 1 + 1) = 저장소 최소. ⚙삼진 **38.04M**, packed **9.61MB(−26.3%)**,
    fp32 상주 **323.2MB(−28.4%)**.

    ★**이 프리셋의 존재 이유는 예측을 검정하는 것**이다. 결과 032 §4 가 g16 과 p1c1 이
    **같은 효율선**(0.0035~0.0041 nats/유니크삼진 100만)에 있음을 관측했고, 그 국소 선형을
    이 구성에 적용하면 **Δ ≈ +0.062** 다. 대가가 **더해지면** 선형이 유지되고, **덜하면**
    두 레버가 같은 자유도를 뺏고 있다는 뜻이며, **더하면** 상호작용이 있다.
    **어느 쪽이든 정보다.**

    부모 재사용 가능: `n_middle=16, g=16` 이라 `teacher.mid_mlps[0..15]` 로 정확히 맞는다.
    ⚠️ 깊이 교락(20→18)은 `m100R1p` 와 동일하게 남는다.
    """
    return dataclasses.replace(_m100R1p(seq, ckpt), mlp_group=16)


def _m100R1d(seq, ckpt):
    """★P049 — **타잉으로 깊이를 사는가**. `m100R1c`(g8, 중간 16) 에서 중간층을 **32**,
    `mlp_group` 을 **16** 으로. **유니크 MLP 개수는 6 으로 그대로**(2+2+2)다.

    | | `m100R1c` | **`m100R1d`** |
    |---|---:|---:|
    | 깊이 | 20 | **36** |
    | 유니크 MLP | 6 | **6**(동일) |
    | MLP 삼진 | 28.31M | **28.31M**(완전 동일) |
    | **어텐션 삼진** | 26.54M | **47.78M**(+80.0%) |
    | 총 삼진 | 54.85M | **76.09M**(+38.7%) |

    ★**MLP 는 공짜고 어텐션 값을 낸다.** 어텐션은 타잉 대상이 아니라 층마다 독립이기 때문이다.
    그래서 이 프리셋이 묻는 것은 *"상주 +35.9% 를 내고 깊이 20→36 을 사면 그만큼 좋아지는가"* 다.
    **채택 임계는 결과 전에 못 박았다 — paired Δ < −0.075**(계획 P049 §3).

    ⚠️ **부모 dense 는 20층**이라 36층 학생에 그대로 이식할 수 없다. `init_from_dense` 의
    **깊이 확장 이식**(2026-08-14 구현)이 선결이고, 그 동작은 **`run_P049_stage0_init_gate.bat`
    이 먼저 검정**한다. 게이트를 통과하기 전에는 단계1 을 돌리지 않는다(결과 030 의 교훈).
    """
    return dataclasses.replace(_m100R1c(seq, ckpt), n_middle=32, mlp_group=16)


def _m100s(n_mid):
    """★P074(2026-08-26) — **얕은 dense 대조군**. `m100` 에서 `n_middle` **한 필드만** 바꾼다.

    ★왜 필요한가(사용자 지시 2026-08-26): 우리 논지는 *"타잉으로 상주를 줄인다"* 인데
    **한 번도 물어본 적 없는 반사실**이 있다 — 🚫*"같은 상주를 그냥 **얕은 dense** 로 쓰면?"*
    타잉 20층과 dense 9층의 상주가 비슷하다면, **타잉이 얕음보다 나은지**를 보여야 한다.

    ⚠️**층수를 바꾸면 `--init-from` 이 얕은 쪽으로 이식해야 한다** — `_depth_map` 이
    지원하지만 **`--depth-init role` 을 명시**해야 한다(`init_utils.py` §116).
    """
    # ⚠️★**`mlp_group` 도 함께 내린다.** `m100` 은 `mlp_group=4` 인데 `__post_init__` 이
    #   `n_middle % mlp_group == 0` 을 단언한다 — `n_middle` 만 2 나 6 으로 바꾸면
    #   **프리셋 생성 시점에 죽는다.** `--arch dense` 는 `tie_mlp=False` 라 이 값을 안 쓰지만
    #   단언은 그보다 먼저 돈다. ★2 로 두면 2·4·6·8 을 전부 나눈다.
    #   🚫**이 프리셋들은 `--arch dense` 전용이다** — tied 로 쓰면 g2 라는 뜻이 된다.
    return lambda seq, ckpt: dataclasses.replace(_m100(seq, ckpt),
                                                 n_middle=n_mid, mlp_group=2)


PRESETS = {"tiny": _tiny, "m100": _m100, "m100d": _m100d,
           "m100s2": _m100s(2), "m100s4": _m100s(4),
           "m100s6": _m100s(6), "m100s8": _m100s(8),
           # ★P079(2026-08-31) — 16층 dense. `m100s*` 은 n_middle 이므로 12 + prelude/coda 4.
           #   깊이 축 8/12/16/20 에서 16 만 없었다(8=m100s4, 12=m100s8, 20=m100 dense).
           "m100s12": _m100s(12),
           "m100R1a": _m100R1a, "m100R1c": _m100R1c,
           "m100R1p": _m100R1p, "m100R1q": _m100R1q,
           "m100R1d": _m100R1d}


def mlp_group_index(cfg, j: int) -> int:
    """중간층 `j` 가 속한 **유니크 MLP 인덱스**. ★`mlp_split` 규약의 단일 소스.

    ⚠️**여기서만 정한다.** 종전에 `transformer.py` 와 `init_utils.py` 가 각자
    `j // g` 를 쓰고 있었는데, 불균등이 들어오면 **두 곳이 어긋나는 순간
    "이식했다고 믿는데 안 된"** 상태가 된다 — 결과 041·P057 이 지불한 형태다
    (계측함정 18: 적용 대상 집합을 두 곳에서 정의).
    """
    # ★★2026-08-27 — **`tie_mlp=False`(dense) 에서는 층마다 자기 MLP 다.**
    #   지금까지 이 함수는 `tie_mlp` 를 안 봤고, 바로 위 `n_mlp_groups` 는 봤다.
    #   그래서 **같은 파일 안에서 둘이 서로 다른 규약을 말하고 있었다** —
    #   dense 학생을 부모초기화하는 순간 `mlp_group_members` 가 빈 목록을 돌려
    #   `ZeroDivisionError` 로 죽었다(P074 단계1, 로그 059 — 네 팔 전부).
    #   계측함정 18 그대로다: **적용 대상 집합을 두 곳에서 정의했다.**
    if not getattr(cfg, "tie_mlp", True):
        return j                                       # dense = 층당 하나. `n_mlp_groups` 와 같은 규약
    split = tuple(getattr(cfg, "mlp_split", ()) or ())
    if not split:
        return j // cfg.mlp_group                      # 종전 = 비트 동일
    import bisect
    return bisect.bisect_right(split, j)


def mlp_group_members(cfg, gi: int):
    """유니크 MLP `gi` 가 덮는 **중간층 인덱스 목록**. `mlp_group_index` 의 역함수."""
    return [j for j in range(cfg.n_middle) if mlp_group_index(cfg, j) == gi]


def n_unique_mid_mlp(cfg) -> int:
    # ★동일 사유로 `tie_mlp` 를 먼저 본다(2026-08-27). `n_mlp_groups` 와 항상 같아야 한다.
    if not getattr(cfg, "tie_mlp", True):
        return cfg.n_middle
    split = tuple(getattr(cfg, "mlp_split", ()) or ())
    return (len(split) + 1) if split else (cfg.n_middle // cfg.mlp_group)


def build_config(preset: str, arch: str, seq: int, ckpt: bool = True) -> TMTConfig:
    if preset not in PRESETS:
        raise KeyError(f"unknown preset {preset!r}; 있는 것: {list(PRESETS)}")
    cfg = PRESETS[preset](seq, ckpt)
    return cfg if arch == "tied" else dense_baseline(cfg)
