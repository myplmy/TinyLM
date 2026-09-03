"""TiedMLPTransformer (v5) — 조립.

v4 대비 변경(학습 발산 대응, 메모리·파라미터·FLOPs 중립):
  A. QK-norm (modules.Attention).  B. torch.compile 안전 어닐(_anneal 버퍼 + set_anneal).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from ..config import TMTConfig, dense_baseline  # noqa: F401  (재export)
from ..config import mlp_group_index as _mlp_gi   # ★P061 그룹 인덱스 단일 소스
from .ternary import TLinear, ternary  # noqa: F401
# ★2026-08-14 — `build_attention` 이 **import 목록에 없었다.** `attn_group > 1` 경로만
#   그것을 부르므로(아래 `mid_attns`), 기본 경로는 멀쩡하고 **P057 을 켠 순간에만**
#   `NameError: name 'build_attention' is not defined` 로 죽었다(로그 044, 3팔 전부).
#   스모크는 `attn_group=1` 만 돌아서 통과했다 — 계측함정 37.
from .modules import (RMSNorm, Attention, MLP, Layer, build_attention,  # noqa: F401
                      build_rope, apply_rope)
from .ternary import LoRA  # noqa: F401


class TiedMLPTransformer(nn.Module):
    def __init__(self, cfg: TMTConfig):
        super().__init__()
        self.cfg = cfg
        E = cfg.emb_rank if cfg.emb_rank else cfg.dim

        self.emb = nn.Embedding(cfg.vocab_size, E)
        nn.init.normal_(self.emb.weight, std=0.02)
        self.emb_up = nn.Linear(E, cfg.dim, bias=False) if cfg.emb_rank else None
        if cfg.emb_rank:
            nn.init.normal_(self.emb_up.weight, std=0.02)

        self.pre_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_prelude)])
        self.mid_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_mlp_groups)])
        self.coda_mlps = nn.ModuleList([MLP(cfg) for _ in range(cfg.n_coda)])

        # ★P057(2026-08-13) — **어텐션 타잉.** `attn_group` g 면 중간층 g 개가 어텐션 하나를 공유한다.
        #   MLP 타잉과 **완전히 같은 형태**(`mid_mlps[j // mlp_group]`)라 코드가 대칭이다.
        #   기본 `attn_group = 1` = 층마다 독립 = **종전 = 비트 동일.**
        #
        #   ★왜 이 축인가: 삼진 54.85M 중 **어텐션이 26.54M = 48.4%** 인데 타잉 대상이 아니었다.
        #   MLP 축은 P045(g16)에서 종결됐고 이쪽은 손도 안 댔다(REVIEW2 §5.2 · 외부문서 E §9).
        #
        #   ⚠️ **CLA 와 겹친다.** `cla_group=2` 는 이미 K/V 를 공유 중이라, 공유 어텐션이
        #      **소유층/재사용층 양쪽에 선다.** 소유 여부는 층이 정하고 어텐션 객체는 그
        #      호출에서 `kv` 를 받으므로 동작은 성립하지만, **대가를 귀속하려면 `cla_group=1`
        #      대조가 필요**하다(계획 P057).
        ag = int(getattr(cfg, "attn_group", 1) or 1)
        self.mid_attns = None
        if ag > 1:
            assert cfg.n_middle % ag == 0, f"n_middle {cfg.n_middle} % attn_group {ag} != 0"
            # 공유 어텐션은 **K/V 를 소유하는 형태**로 만든다 — 그래야 어느 위치에 서든
            # 필요한 projection 이 다 있다. 소유 여부는 호출 시 `kv` 인자가 정한다.
            self.mid_attns = nn.ModuleList([build_attention(cfg, True)
                                            for _ in range(cfg.n_middle // ag)])

        layers, self.owner = [], []
        for i in range(cfg.n_layers):
            # ★★P084 — `cla_edges=False` 면 prelude·coda 는 **자기 K/V 를 갖는다.**
            #   그룹은 **middle 안에서만** 묶는다 — 전역 인덱스로 나누면 그룹이
            #   머리/몸통 경계를 걸쳐 *'머리 하나 + 몸통 하나'* 가 짝이 된다.
            _p, _m = cfg.n_prelude, cfg.n_middle
            if cfg.cla_edges or cfg.cla_group == 1:
                _own = i - (i % cfg.cla_group)          # 종전 = 비트 동일
            elif _p <= i < _p + _m:
                _j = i - _p                             # middle 내부 좌표로 묶는다
                _own = _p + (_j - (_j % cfg.cla_group))
            else:
                _own = i                                # 머리·꼬리는 자기 것
            owns = (_own == i)
            self.owner.append(_own)
            shared_attn = None
            if i < cfg.n_prelude:
                mlp = self.pre_mlps[i]
            elif i < cfg.n_prelude + cfg.n_middle:
                j = i - cfg.n_prelude
                # ★P061: 그룹 인덱스는 `config.mlp_group_index` 가 **단일 소스**다.
                #   `mlp_split` 이 비면 `j // mlp_group` 과 동일 = 비트 동일.
                mlp = self.mid_mlps[_mlp_gi(cfg, j) if cfg.tie_mlp else j]
                if self.mid_attns is not None:
                    shared_attn = self.mid_attns[j // ag]
            else:
                mlp = self.coda_mlps[i - cfg.n_prelude - cfg.n_middle]
            is_mid_tied = (cfg.n_prelude <= i < cfg.n_prelude + cfg.n_middle) and cfg.tie_mlp
            layers.append(Layer(cfg, owns, mlp, mlp_lora=is_mid_tied, mlp_film=is_mid_tied,
                                # ★★2026-09-04 정정 — **타잉 여부와 무관하게** 중간층에 붙인다.
                                #   🚫우리 32 MiB 승자는 `--arch dense`(tie_mlp=False)라
                                #   `is_mid_tied` 로 걸면 **플래그가 아무 일도 안 한다**
                                #   (스모크 커버리지 게이트가 잡았다). 논문도 **모든 행렬층**이 대상이다.
                                mlp_lrm=(cfg.n_prelude <= i < cfg.n_prelude + cfg.n_middle),
                                attn=shared_attn))
        self.layers = nn.ModuleList(layers)

        self.norm_f = RMSNorm(cfg.dim, cfg.norm_eps)
        self.norm_f_scale = nn.Parameter(torch.ones(cfg.dim))

        if cfg.n_modes > 1:
            self.router = nn.Linear(cfg.dim, cfg.n_modes, bias=False)
            nn.init.normal_(self.router.weight, std=0.02)
            self.router_bias = nn.Parameter(torch.zeros(cfg.n_layers, cfg.n_modes))

        cos, sin = build_rope(cfg.head_dim, cfg.max_seq_len, cfg.rope_theta)
        self.register_buffer("rope_cos", cos, persistent=False)
        self.register_buffer("rope_sin", sin, persistent=False)

        # v5: 삼진 어닐 계수를 버퍼로 → torch.compile 재컴파일 방지.
        self.register_buffer("_anneal", torch.tensor(float(cfg.quant_anneal)), persistent=False)
        self._tlinear_cache = list(self._tlinears())   # ②: 매 forward 모듈 트리 순회 제거(plain list)
        self._quant_frozen = False                     # freeze_quant() 참조(추론 전용 최적화)
        self._int8_store = False                       # P034 단계3
        self._lut_store = False                        # ★P014 단계1 (LUT 배포 경로)
        self._unpack_cache = False                     # P034 단계3C (기본 off = 종전 경로)
        self._unpack_gen = 0
        self._cacheable_mlps = []
        self._armed_tlinears = []
        self._arena = None                             # P036 Arenas λ_t (None = 항 없음)
        self._arena_v = 0.0

    # ---------- quantization ----------
    def _tlinears(self):
        for m in self.modules():
            if isinstance(m, TLinear):
                yield m

    def set_anneal(self, v: float):
        self._anneal.fill_(float(v))
        self.cfg.quant_anneal = float(v)

    def set_lora_scale(self, v: float):
        """★P008 — 층별 LoRA 의 출력 스케일 s(t) 를 설정한다.

        **s=1 이면 고정 LoRA(종전), s=0 이면 LoRA 가 완전히 사라진다.**
        학습 중 1 → 0 으로 어닐하면 **초반에는 층별 특화(≈untied), 종료 시 순수 타잉**이 된다.
        그리고 s=0 이므로 **배포 메모리 대가가 0** 이다 — 이것이 고정 LoRA(1.82×→1.71×)와
        결정적으로 다른 점이다.

        ★삼진 어닐(`set_anneal`)과 **같은 원리·같은 구현 패턴**이다:
        제약을 처음부터 걸지 않고 학습이 진행되며 점진적으로 조인다.

        적용 대상은 **모든 `LoRA` 모듈 하나의 집합**으로만 정한다 — 결과 016 §14 의 교훈
        ("적용 대상 집합을 두 곳에서 따로 정하면 한쪽만 고쳐도 통과한다").
        """
        for m in self.modules():
            if isinstance(m, LoRA):
                m._scale.fill_(float(v))

    def set_arena(self, v: float):
        """P036 Arenas 의 λ_t 를 설정한다. **0 이면 항이 완전히 사라진다**(배포 상태)."""
        self._arena_v = float(v)
        if self._arena is None:
            self._arena = torch.tensor(float(v), device=self.emb.weight.device)
        else:
            self._arena.fill_(float(v))

    def refresh_quant(self):
        # ★arena 는 λ_t ^> 0 일 때만 전달한다 → 기본 학습·추론 경로는 종전과 **비트 동일**.
        ar = self._arena if (self._arena is not None and self._arena_v > 0.0) else None
        for m in self._tlinear_cache:
            m.refresh_quant(self._anneal, ar)

    def clear_quant(self):
        self._quant_frozen = False
        for m in self._tlinear_cache:
            m.clear_quant()

    def latent_dropped(self):
        """P034 단계2 가 적용됐는지. `mem_breakdown()` 의 상주 계산이 이 값을 본다."""
        return any(m.latent_dropped() for m in self._tlinear_cache)

    def drop_latent(self):
        """★P034 단계2 — 추론 시 fp32 latent 가중치를 해제한다(되돌릴 수 없다).

        `freeze_quant()` 이후에만 유효하다. backward 가 없는 추론에서 latent 는 죽은 무게이고,
        결과 016 의 실측식(상주 = 유니크삼진 × 4B × **2벌** + 나머지)에서 그 2벌 중 한 벌이다.
        커스텀 커널 없이 **상주를 약 절반**으로 줄이는 오늘 가능한 최대 레버다.

        ⚠️ 학습 재개 불가. `clear_quant()` 로도 되돌아오지 않는다 — 다시 쓰려면 재로드한다.
        """
        if not self._quant_frozen:
            raise RuntimeError("drop_latent() 전에 freeze_quant() 가 필요하다.")
        for m in self._tlinear_cache:
            m.drop_latent()

    def to_int8(self):
        """★P034 단계3 — 삼진 dequant 사본을 int8 코드 + fp32 α 로 저장한다.

        `drop_latent()` 와 함께 쓰는 것이 정상 순서다(latent 해제 → int8 저장).
        되돌릴 수 없다. 추론 전용.
        """
        if not self._quant_frozen:
            raise RuntimeError("to_int8() 전에 freeze_quant() 가 필요하다.")
        for m in self._tlinear_cache:
            m.to_int8()
        self._int8_store = True

    def int8_stored(self):
        return getattr(self, "_int8_store", False)

    def to_lut(self):
        """★★P014 단계1 — 삼진을 **LUT 코드(1.600 bpw)** 로 바꾼다. 되돌릴 수 없다.

        정상 순서: `freeze_quant()` -> `drop_latent()` -> **`to_lut()`**.
        `to_int8()` 을 먼저 불렀으면 그것을 이어받고, 안 불렀으면 내부에서 부른다.

        ★**이것이 40 MiB 목표의 필수 조건**이다 — 결과 052 §3.1: int8 로는 임베딩을
        ternary 까지 눌러도 39.5 로 아슬하고, LUT 면 여유가 생긴다.
        """
        if not self._quant_frozen:
            raise RuntimeError("to_lut() 전에 freeze_quant() 가 필요하다.")
        for m in self._tlinear_cache:
            m.to_lut()
        self._int8_store = False
        self._lut_store = True
        n = sum(m.lut_bytes() for m in self._tlinear_cache)
        print(f"[lut] ★삼진 {len(self._tlinear_cache)}개 층 -> LUT 코드. "
              f"상주 {n/2**20:.2f} MiB (코드 + per-row alpha)")
        print(f"[lut] ⚠️★per-row alpha 로 재추정했다 — 대가는 결과 028 이 쟀다"
              f"(+0.0038~0.0068 bpb, 분해능 0.008 미만)")

    def lut_stored(self):
        return getattr(self, "_lut_store", False)

    def lut_bytes(self):
        return sum(m.lut_bytes() for m in self._tlinear_cache)

    # ---------- P034 단계5 : 임베딩 (★설계 미완 — 구현하지 않는다) ----------
    #
    # ★★2026-08-06 발견 — **임베딩은 지금까지 한 번도 양자화된 적이 없다.**
    #   `cfg.quantize_embedding=True` 는 `mem_breakdown()` 의 **저장(packed) 계산에만** 쓰이고
    #   (`e_bits = b_e if cfg.quantize_embedding else 16`), `self.emb` 는 평범한
    #   `nn.Embedding`(fp32) 이다. 즉 `packed_mb` 27.1MB 는 삼진뿐 아니라 **임베딩 쪽에서도
    #   아직 없는 포맷을 가정**하고 있다. 상주 33.0MB 중 32.8MB 가 이것이다(mC 상주의 38%).
    #
    # ★그런데 단순 int8 화가 **성립하지 않는다** — 임베딩이 **출력 헤드와 묶여 있기 때문**이다:
    #       logits = F.linear(F.linear(x, emb_up.weight.t()), self.emb.weight)
    #   조회(lookup)는 행 몇 개만 되돌리면 되지만, **헤드는 (32768, 256) 전체를 GEMM 에 넣는다.**
    #   int8 로 저장하고 헤드에서 fp32 로 되돌리면 **forward 마다 32.8MB 를 쓰고 읽는다** —
    #   결과 016 §13 에서 실측한 대가(0.1035 ms/tok per MB)로 환산하면 **+3.4ms/토큰(약 +5%)** 이고,
    #   무엇보다 **§13 이 방금 저지른 것과 같은 종류의 트레이드**다. 설계를 마치기 전에는 넣지 않는다.
    #
    # 선택지(계획 P034 §단계5 에 기록):
    #   (a) 헤드를 임베딩에서 분리(untie) — 파라미터 +8.4M. **메모리 목표와 정면 충돌**
    #   (b) 헤드를 int8 GEMM 으로(`torch._int_mm`) — 활성값도 int8 여야 한다. 연구 과제
    #   (c) 어휘 축소 — P039(어휘 활용도 진단)가 **미학습 토큰을 찾으면** 32,768 을 줄일 수 있다.
    #       ★같은 33MB 를 **양자화 없이** 줄이는 유일한 경로이고, **선결 실험이 이미 설계돼 있다**
    #   (d) 임베딩 랭크 축소(E=256 → 128) — 재학습 필요. 품질 영향 미지
    #
    # → **(c) 가 가장 값싸고 위험이 낮다. P039 를 먼저 돌린다.**

    # ---------- ★P034 단계5 : 임베딩 양자화 (2026-08-22 구현) ----------
    #
    # ★설계 근거 = 계획 P034 §11. 요점 셋:
    #   ① 입력 조회는 행 몇 개만, **출력 헤드는 V행 전부**를 매 스텝 GEMM 에 넣는다.
    #   ② 그래서 순진한 int8 은 상주를 **늘린다**(저장 8.32 + 복원 32.75 > 32.75).
    #      -> **청크 복원**으로 동시 버퍼를 `C × E × 4B` 로 묶는다(P053 이 KD 손실에 쓴 수법).
    #   ③ ★**BF16 은 복원이 아예 필요 없다** — forward 가 이미 autocast(bf16) 안이라
    #      `F.linear` 가 어차피 bf16 으로 캐스팅한다. 저장을 bf16 으로 바꾸면 **캐스팅이 사라진다.**
    #
    # ⚠️ **배포(추론) 전용**이다. `to_int8()`·`drop_latent()` 와 같은 계열이고 되돌릴 수 없다.
    #    학습 중 `emb` 는 fp32 master 로 남는다.

    def quantize_embedding(self, fmt="bf16", group=64):
        """`emb.weight` 를 `fmt` 로 바꾼다. `fmt in {bf16, fp16, int8, int4, ternary}`.

        - **bf16/fp16**: 파라미터 dtype 만 바꾼다. **복원 없음.**
        - **int8/int4/ternary**: 코드 + 스케일로 저장하고 **헤드에서 청크 복원**한다.
          입력 조회(`self.emb(tokens)`)도 그 경로를 거친다(행 몇 개라 싸다).
        """
        import torch
        if getattr(self, "_emb_fmt", None) is not None:
            raise RuntimeError(f"이미 양자화됐다: {self._emb_fmt} (되돌릴 수 없다)")
        w = self.emb.weight.detach()
        V, E = w.shape
        if fmt in ("bf16", "fp16"):
            dt = torch.bfloat16 if fmt == "bf16" else torch.float16
            self.emb.weight.data = w.to(dt)
            # ★★★2026-08-23 실사고 — **`emb_rank` 모델에는 `emb_up` 이 뒤따른다.**
            #   임베딩만 bf16 으로 바꾸면 `emb_up`(fp32)과 dtype 이 안 맞아
            #   `RuntimeError: expected m1 and m2 to have the same dtype` 로 죽는다.
            #   ⚠️**`emb_rank=0` 인 모델에서는 안 나던 버그**라 스모크가 못 잡았다 —
            #   `tiny` 프리셋에 `emb_rank` 가 없다(함정 37 계열: 그 축을 켠 팔이 없었다).
            #   ★해법(2026-08-23 1차): **다음 층도 같이 내린다.**
            #   🚫★**2026-08-24 정정 — 1차 해법은 오류를 한 층 더 깊은 곳으로 밀었을 뿐이다.**
            #   활성값이 bf16 인 채 삼진 층에 도착해 `F.linear(x_bf16, wq_fp32)` 로 죽었다
            #   (결과 016 §20 의 E2). ★**저장 형식과 계산 형식은 다르다** — 가중치는
            #   bf16 으로 두되 `forward` 가 임베딩 출력을 **fp32 로 되돌린다**.
            #   int8·ternary 는 `_emb_rows()` 가 처음부터 그렇게 하고 있었다.
            if self.emb_up is not None:
                self.emb_up.weight.data = self.emb_up.weight.data.to(dt)
            self._emb_fmt = fmt
            self._selftest_after_quant(fmt)
            return
        if fmt == "int8":
            g = E                                   # per-row (행당 스케일 1개)
        elif fmt == "int4":
            g = group
            if E % g:
                raise ValueError(f"emb_rank {E} 가 group {g} 로 안 나눠진다")
        elif fmt == "ternary":
            g = E
        else:
            raise ValueError(f"모르는 fmt: {fmt!r}")
        wg = w.reshape(V, E // g, g)
        if fmt == "ternary":
            # TWN 과 같은 규약: 문턱 이상만 살리고 α = 살아남은 |w| 의 평균
            aw = wg.abs()
            mask = (aw >= self.cfg.twn_thr_ratio * aw.mean(dim=2, keepdim=True)).to(w.dtype)
            cnt = mask.sum(dim=2, keepdim=True).clamp_min(1.0)
            scale = (aw * mask).sum(dim=2, keepdim=True) / cnt
            code = (torch.sign(wg) * mask).to(torch.int8)
        else:
            qmax = 127.0 if fmt == "int8" else 7.0
            scale = wg.abs().amax(dim=2, keepdim=True) / qmax
            code = torch.round(wg / scale.clamp_min(1e-12)).clamp(-qmax, qmax).to(torch.int8)
        # ⚠️★★**여기가 회계의 함정이다.** `code` 는 fmt 와 무관하게 **`torch.int8` 텐서**다 —
        #   PyTorch 에 int4/ternary dtype 이 없다. 즉 **int4·ternary 는 저장이 안 준다.**
        #   ★줄이려면 **패킹이 필요**하고 그것은 `model/lut.py` 의 일이다(P014).
        #   🚫**"int4 로 바꿨으니 절반" 이라고 쓰면 그것은 계산이지 실측이 아니다**(함정 1).
        self._emb_code = code.reshape(V, E).contiguous()
        self._emb_scale = scale.squeeze(-1).contiguous().float()      # (V, E//g)
        self._emb_g = g
        self._emb_fmt = fmt
        self.emb.weight.data = torch.empty(0, device=w.device, dtype=w.dtype)  # ★fp32 해제

    def _selftest_after_quant(self, fmt):
        """★2026-08-26 — 양자화 **직후** 1토큰 forward 를 돌려 dtype 누수를 여기서 잡는다.

        🚫**왜 필요한가**: `--emb-quant bf16` 은 **세 번** 죽었고 세 번 다
        `mem_runtime.py` 의 생성 단계에서, 즉 **변이 지점에서 수십 프레임 떨어진 곳**에서
        터졌다. 그러면 *"어디를 고쳐야 하는가"* 가 매번 새로 보인다.
        ★**여기서 터지면 원인이 한 줄로 보인다.**

        ⚠️계측 부담 0 에 가깝다(토큰 1개). ⚠️**이것은 정확성 시험이 아니다** —
        *"경로가 도는가"* 만 본다(정확성은 `paired_eval` 의 몫).
        """
        import torch as _t
        try:
            with _t.no_grad():
                idx = _t.zeros((1, 1), dtype=_t.long, device=self.emb.weight.device)
                self.eval()
                _ = self(idx)
        except RuntimeError as e:
            raise RuntimeError(
                f"[emb-quant] ★양자화({fmt}) 직후 1토큰 forward 가 실패했다 — "
                f"**저장 dtype 이 계산 경로로 샜다.** 소비 지점은 넷이고 "
                f"`_emb_w()`·`_emb_up_w()` 접근자를 거쳐야 한다(결과 016 §21).\n"
                f"  원본 오류: {e}") from e

    def _emb_rows(self, idx=None):
        """양자화된 임베딩을 fp32 로 되돌린다. `idx=None` 이면 전체, 아니면 그 행만."""
        code = self._emb_code if idx is None else self._emb_code[idx]
        sc = self._emb_scale if idx is None else self._emb_scale[idx]
        n, E = code.shape
        g = self._emb_g
        return (code.reshape(n, E // g, g).to(sc.dtype)
                * sc.unsqueeze(-1)).reshape(n, E)

    def embedding_quantized(self):
        return getattr(self, "_emb_fmt", None)

    # ★★★2026-08-26 (결과 016 §21) — **저장 dtype 이 계산 경로로 새는 것을 여기서 막는다.**
    #
    #   🚫**같은 오류를 세 번 고쳤고 세 번 다 다른 곳에서 터졌다**:
    #     1차(08-23) `emb` 만 bf16      -> `emb_up`(fp32) 과 충돌
    #     2차(08-23) `emb_up` 도 내림   -> **삼진 층**에서 충돌(활성값이 bf16 인 채 흘렀다)
    #     3차(08-24) forward 에서 `.float()` -> ★**출력 헤드**에서 충돌(가중치가 아직 bf16)
    #
    #   ★원인은 하나다: **`emb.weight`·`emb_up.weight` 는 네 곳에서 소비된다**
    #   (입력 조회 / 입력 up / 헤드 up / 헤드 logits). **한 곳씩 고치면 영원히 끝나지 않는다.**
    #   → ★**소비 지점을 접근자 둘로 단일화한다**(함정 18 의 처방: 정본을 한 곳에).
    #
    #   ★규약: **양자화 포맷은 저장 형식이다.** int8·ternary 는 `_emb_rows()` 가 fp32 를
    #   돌려주고 있었다. bf16·fp16 도 **같은 규약**을 따른다 — 저장은 좁게, 계산은 fp32.
    def _emb_w(self):
        """입력·헤드가 공유하는 임베딩 표. **항상 계산 dtype(fp32)으로 돌려준다.**"""
        w = self.emb.weight
        return w if w.dtype == torch.float32 else w.float()

    def _emb_up_w(self):
        """`emb_rank` 병목 행렬. 위와 같은 규약."""
        w = self.emb_up.weight
        return w if w.dtype == torch.float32 else w.float()

    def _head_logits(self, x):
        """출력 헤드. 양자화 시 **어휘를 청크로 잘라** 동시 fp32 버퍼를 묶는다.

        ★청크 크기 `cfg.emb_chunk`(기본 0 = 끄기). 4096 이면 버퍼 `4096×E×4B` = 4 MiB(E=256).
        """
        if self.emb_up is not None:
            x = F.linear(x, self._emb_up_w().t())          # ★2026-08-26 접근자 경유
        fmt = getattr(self, "_emb_fmt", None)
        if fmt is None or fmt in ("bf16", "fp16"):
            return F.linear(x, self._emb_w())              # ★2026-08-26 접근자 경유
        C = int(getattr(self.cfg, "emb_chunk", 0) or 0)
        V = self._emb_code.shape[0]
        if C <= 0 or C >= V:
            return F.linear(x, self._emb_rows())
        import torch
        outs = [F.linear(x, self._emb_rows(slice(v0, min(v0 + C, V))))
                for v0 in range(0, V, C)]
        return torch.cat(outs, dim=-1)

    def enable_unpack_cache(self, on=True):
        """★P034 단계3C — int8 언팩 결과를 **유니크 모듈당 1회**로 줄인다(타잉 전용 이득).

        근거: `docs/20260806_레이어타이잉-메모리와속도-원인분석.md` §5.
        `forward()` 는 층마다 `TLinear.forward()` 를 부르고, 타이된 층들은 **같은 객체**를
        공유한다. 그런데 `_wq_from_i8()` 은 호출마다 fp32 로 되돌리므로 g8 이면 **같은 언팩을
        16번** 한다. 세대 카운터로 한 번만 돌게 만든다.

        ★★2차 구현(2026-08-06, 결과 016 §13 의 사고 대응). 1차는 두 가지가 틀렸다:

          ① **공유되지 않는 모듈까지 캐시했다.** dense 는 모든 TLinear 가 층당 1회라 적중이
             0 인데 버퍼만 20층분(472.5MB) 남았다 → `p6d` 가 **40% 느려졌다.**
             지금은 **층이 2회 이상 참조하는 MLP 의 TLinear 에만** 캐시를 켠다.
             **dense 는 켤 대상이 하나도 없어 종전 경로와 완전히 동일하다.**
          ② **버퍼를 다음 forward 까지 들고 있었다.** 지금은 `forward()` 가 **그룹을 벗어나는
             순간** 해제한다(층 스케줄이 `mid_mlps[j//g]` 라 같은 MLP 가 연속으로 온다)
             → 동시에 사는 버퍼는 **MLP 한 벌(약 18.9MB)** 이 상한이다.

        ⚠️ **`to_int8()` 을 쓴 추론 경로 전용**이다. 학습에는 의미가 없다(latent 가 매 스텝 바뀐다).
        ⚠️ 기본 off. 켜도 **결과는 비트 동일**해야 한다 — 다르면 구현이 틀린 것이고,
           `scripts/mem_runtime.py` 의 로짓 동등성 게이트가 `0.000e+00` 로 그것을 확인한다.
           **그리고 그 도구는 캐시 바이트도 함께 센다** — §13 은 안 세서 못 잡았다.
        """
        from collections import Counter
        self._unpack_cache = bool(on)
        for m in self._tlinear_cache:                 # 항상 전부 끄고 시작(재호출 안전)
            m.set_unpack_gen(None)
        self._cacheable_mlps = []
        self._armed_tlinears = []                     # ★3차 수정(§14): 무장된 것만 따로 든다
        if not on:
            return
        # ★공유 판정 = "몇 개의 층이 이 MLP 객체를 참조하는가". 1이면 캐시할 이유가 없다.
        cnt = Counter(id(l.mlp[0]) for l in self.layers)
        seen = set()
        for l in self.layers:
            k = id(l.mlp[0])
            if cnt[k] > 1 and k not in seen:
                seen.add(k)
                self._cacheable_mlps.append(l.mlp[0])
        for mlp in self._cacheable_mlps:
            for sub in mlp.modules():
                if isinstance(sub, TLinear):
                    sub.set_unpack_gen(0)
                    self._armed_tlinears.append(sub)

    @staticmethod
    def _clear_mlp_unpack(mlp):
        for sub in mlp.modules():
            if isinstance(sub, TLinear):
                sub.clear_unpack_cache()

    def unpack_cache_mb(self):
        """언팩 캐시가 지금 쥐고 있는 MB. **상주 회계에 반드시 포함**한다(결과 016 §13)."""
        return sum(m.unpack_cache_bytes() for m in self._tlinear_cache) / 1024 ** 2

    def unpack_cached(self):
        return getattr(self, "_unpack_cache", False)

    def freeze_quant(self):
        """★추론용: 삼진 가중치를 **한 번만** 계산하고 이후 forward 에서 재계산하지 않는다.

        `forward()` 는 매 호출마다 `refresh_quant()` 를 부른다(학습 중에는 latent weight 가
        스텝마다 바뀌므로 **반드시 그래야 한다**). 그런데 추론에서는 가중치가 고정이라
        그 재계산이 전부 낭비다. 결과 014 에서 이 비용이 **CPU 추론 시간의 약 79%** 를
        차지했고, sparse34 는 `argmin`+`scatter_` 경로라 더 비쌌다(mA 가 dense 보다 느려 보인 원인).

        되돌리려면 `clear_quant()` 를 부른다(학습 재개 시 필수). 그래서 `clear_quant` 가
        플래그를 함께 내린다 — 안 그러면 얼어붙은 가중치로 학습하게 된다.
        """
        self.refresh_quant()
        self._quant_frozen = True

    # ---------- P049B : 학습 시 재귀 스케줄 ----------
    def _repeat_schedule(self, R):
        """★P049B(2026-08-13) — **학습 경로의 중간 블록 반복 스케줄.**

        `repeat_mode` 세 가지(사용자 지시 2026-08-13):

        | 모드 | 무엇 |
        |---|---|
        | `uniform` | 중간 16층 **전체**를 R 회 통과 (b) 전체 층 반복 |
        | `block` | `repeat_block` 이 가리키는 **MLP 그룹만** R 회 (a) 특정 층만 반복 |
        | `progressive` | 층이 깊을수록 반복 수가 **점진 증가** (c) 점진 조절 |
        | ★**`inplace`** | **각 층을 제자리에서 R 회** — ★**추론 `--repeat-where even` 의 학습 짝** |

        ★★**`uniform` ↔ 추론 `front`/`back`(extra == m 일 때)** 이 정확히 같은 스케줄이고,
        ★★**`inplace` ↔ 추론 `even`** 이 짝이다. **짝을 안 맞추면 함정 39 다.**

        ⚠️ prelude·coda 는 **건드리지 않는다**(P031 과 같은 규약). 그쪽은 타잉 대상이 아니고
           역할이 다르다.

        ⚠️★**KV 소유 규약**: 같은 층을 두 번 지나면 `forward` 의 `(owner, 통과번호)` 키가
           **통과마다 K/V 를 새로 만든다**(기본). `repeat_kv_reuse` 를 켜면 첫 통과 것을
           재사용한다 — **대조 조건**이지 기본이 아니다. 두 번째 통과가 낡은 K/V 를 본다.
        """
        # ★함정 18(2026-08-22) — 유효 목록은 `config.REPEAT_MODES` 하나뿐이다.
        #   여기서도 대조해 **모르는 모드가 조용히 uniform 으로 떨어지는 것**을 막는다.
        from ..config import REPEAT_MODES
        _m = str(getattr(self.cfg, "repeat_mode", "uniform") or "uniform")
        assert _m in REPEAT_MODES, f"repeat_mode 미등록: {_m} (정본 config.REPEAT_MODES)"
        cfg = self.cfg
        p, m, g = cfg.n_prelude, cfg.n_middle, cfg.mlp_group
        mode = getattr(cfg, "repeat_mode", "uniform")
        mid = list(range(p, p + m))
        out = list(range(p))                     # prelude 그대로
        if mode == "uniform":
            reps = int(round(R))
            assert reps >= 1, "train_repeat 는 uniform 에서 1 이상 정수로 반올림돼야 한다"
            # ★2026-08-13 — `uniform` 은 **정수 반올림**이라 R=1.5 가 R=2.0 과 같다.
            #   조용히 다른 값을 쓰면 결과문서에 "R=1.5 를 쟀다" 고 적히고 **그건 거짓**이다.
            if abs(R - reps) > 1e-9 and not getattr(self, "_warned_round", False):
                self._warned_round = True
                print(f"[repeat] ⚠️★uniform 은 정수 반올림이다 — **train_repeat {R} -^> {reps} 로 "
                      f"동작한다.** 분수 배수가 필요하면 `--repeat-mode progressive` 를 쓸 것. "
                      f"결과문서에 반드시 {reps} 로 적는다.")
            for _ in range(reps):
                out += mid
        elif mode == "block":
            b = int(getattr(cfg, "repeat_block", 0))
            lo, hi = p + b * g, p + (b + 1) * g
            assert 0 <= b < cfg.n_mlp_groups, f"repeat_block {b} 범위 밖(0..{cfg.n_mlp_groups-1})"
            reps = int(round(R))
            for i in mid:
                out += [i] * (reps if lo <= i < hi else 1)
        elif mode == "inplace":
            # ★★2026-08-22 신설 (사용자 지적) — **추론 `--repeat-where even` 의 학습 짝.**
            #   종전에는 학습 모드가 `uniform`(블록 전체를 R 회) 하나뿐이라
            #   추론에서 `even`(각 층을 제자리에서 R 회)을 주면 **학습과 다른 함수**였다.
            #   결과 047 단계0 의 `even +0.0992` 는 *"even 이 나쁘다"* 가 아니라
            #   ***"학습 안 한 스케줄이라 나쁘다"*** 로 읽어야 한다(함정 39 계열).
            reps = int(round(R))
            assert reps >= 1, "train_repeat 는 inplace 에서 1 이상 정수로 반올림돼야 한다"
            for i in mid:
                out += [i] * reps
        else:                                     # progressive
            # 깊이 비율 t∈[0,1) 에 대해 반복수를 1 → round(R) 로 선형 증가시킨다.
            top = int(round(R))
            for k, i in enumerate(mid):
                t = k / max(m - 1, 1)
                out += [i] * max(1, int(round(1 + (top - 1) * t)))
        out += list(range(p + m, cfg.n_layers))   # coda 그대로
        return out

    # ---------- P031 단계0 : 층 방문 스케줄 ----------
    def visit_schedule(self):
        """forward 가 층을 방문할 순서. **`infer_repeat == 1.0` 이면 `range(n_layers)` 와 동일**하다.

        ★왜 이렇게 정의하나(계획 P031): 공유되는 것은 **MLP 가중치뿐**이고 어텐션·norm 은 층마다
        따로 있다. 그래서 "추론 시 g 를 늘린다"는 성립하지 않는다 — 성립하는 유일한 정의는
        **middle 블록 전체를 R 회 통과**시키는 것이다. prelude·coda 는 건드리지 않는다.

        `total = round(n_middle * R)` 이 middle 통과 횟수다.
          R ^< 1 : middle 에서 `total` 개만 고른다(축소 — 메모리 그대로, 지연만 감소)
          R ^> 1 : 전체를 돈 뒤 `total - n_middle` 개를 더 돈다(확장)
        `repeat_where` 가 **어디를** 더/덜 돌지 정한다. 이 선택이 결과를 바꾸므로
        한 배치만 보고 일반화하지 않는다.
        """
        cfg = self.cfg
        n, p, m = cfg.n_layers, cfg.n_prelude, cfg.n_middle
        R = float(getattr(cfg, "infer_repeat", 1.0) or 1.0)
        # ★P049B(2026-08-13) — **학습 시 재귀.** 학습 중이면 `train_repeat` 이 R 을 정한다.
        #   `infer_repeat`(P031)은 추론 전용이고 결과 020 이 "학습 분포 mismatch" 로 종결했다.
        #   `train_repeat` 은 **그 mismatch 를 학습으로 없애자**는 반대편 축이다.
        #   ⚠️ 둘을 동시에 켜면 어느 것이 반복을 정했는지 알 수 없다 → 즉사시킨다.
        TR = float(getattr(cfg, "train_repeat", 1.0) or 1.0)
        if self.training and TR != 1.0:
            if R != 1.0:
                raise RuntimeError("train_repeat 와 infer_repeat 를 동시에 켤 수 없다 — "
                                   "어느 것이 반복을 정했는지 알 수 없게 된다(함정 2).")
            return self._repeat_schedule(TR)
        # ★★★함정 39 (2026-08-30 수정) — **학습 경로 ≠ 평가 경로.**
        #
        #   🚫**실사고**: `train_repeat=2.0`(36회 통과)으로 학습한 체크포인트를
        #   `eval()` 에서 재면 위 `self.training` 이 False 라 `TR` 이 무시되고
        #   **20회 통과로 평가**됐다. 결과 043 §14 가 그것이고, 재귀 14런 중 **11런이
        #   `val - train_ce` 0.3 을 넘었다**(비재귀 78런은 0건).
        #
        #   ★규약: **평가는 자기가 학습된 함수를 돈다.** 다르게 재고 싶으면
        #   `--infer-repeat` 를 **명시**한다 — 그러면 아래 `R != 1.0` 경로로 간다.
        #   ⚠️**비재귀 체크포인트(TR == 1.0)에는 아무 영향이 없다** = 비트 동일.
        #   ⚠️`_eval_ignores_train_repeat = True` 를 모델에 세우면 옛 거동으로 돌아간다
        #      (그 거동으로 잰 과거 수치를 재현할 때만 쓴다).
        if (not self.training) and TR != 1.0 and R == 1.0 \
                and not getattr(self, "_eval_ignores_train_repeat", False):
            return self._repeat_schedule(TR)
        if R == 1.0:
            return list(range(n))                      # ★기본 경로는 종전과 완전히 같다
        where = getattr(cfg, "repeat_where", "front")
        mid = list(range(p, p + m))
        total = int(round(m * R))
        total = max(1, total)
        if total <= m:                                  # 축소
            k = total
            if where == "front":
                sel = mid[:k]
            elif where == "back":
                sel = mid[-k:]
            else:                                       # even — 균등 간격으로 남긴다
                sel = [mid[round(i * (m - 1) / max(k - 1, 1))] for i in range(k)] if k > 1 else [mid[m // 2]]
            body = sel
        else:                                           # 확장
            extra = total - m
            if where == "front":
                body = mid + mid[:extra] if extra <= m else mid * (total // m) + mid[:total % m]
            elif where == "back":
                body = mid + mid[-extra:] if extra <= m else mid * (total // m) + mid[:total % m]
            else:                                       # even — 균등 간격 층을 제자리에서 한 번 더
                dup = {mid[round(i * (m - 1) / max(extra - 1, 1))] for i in range(extra)} \
                    if extra > 1 else {mid[m // 2]}
                body = [j for jj in mid for j in ((jj, jj) if jj in dup else (jj,))]
        return list(range(p)) + body + list(range(p + m, n))

    # ---------- forward ----------
    def forward(self, tokens, mode_override=None, return_aux=False,
                past_kv=None, use_cache=False):
        """`past_kv` 는 **owner 층 인덱스 → (k, v)** 딕셔너리다.

        ★CLA 주의: KV 를 공유하는 층들은 **캐시도 공유**한다. 그래서 캐시 키는 층 인덱스가
        아니라 `self.owner[i]`(= 그 그룹의 소유 층)이다. 층마다 캐시를 두면 같은 KV 를
        cla_group 배로 중복 저장하게 된다.
        """
        cfg = self.cfg
        B, T = tokens.shape
        # 캐시가 있으면 이번 forward 의 토큰은 past 뒤에 붙는다 → 절대위치가 past_len 만큼 밀린다.
        past_len = 0
        if past_kv:
            past_len = next(iter(past_kv.values()))[0].shape[2]   # (B, n_kv_heads, T, head_dim)
        assert past_len + T <= cfg.max_seq_len, \
            f"past {past_len} + 입력 {T} > max_seq_len {cfg.max_seq_len}"
        if getattr(self, "_emb_fmt", None) in (None, "bf16", "fp16"):
            x = F.embedding(tokens, self._emb_w())         # ★2026-08-26 접근자 경유
        else:                                   # ★P034 단계5 — 코드+스케일에서 행만 되돌린다
            x = self._emb_rows(tokens.reshape(-1)).reshape(*tokens.shape, -1)
        if self.emb_up is not None:
            x = F.linear(x, self._emb_up_w())              # ★2026-08-26 접근자 경유
        # ★RoPE 는 절대위치다. 캐시 사용 시 [:T] 가 아니라 [past_len : past_len+T] 를 써야 한다.
        cos, sin = self.rope_cos[past_len:past_len + T], self.rope_sin[past_len:past_len + T]
        if not self._quant_frozen:
            self.refresh_quant()

        # ★P034 단계3C: 언팩 캐시 세대 갱신. 기본 off 면 이 블록이 통째로 건너뛰어진다.
        #   ★★3차 수정(결과 016 §14) — 종전에는 `self._tlinear_cache`(전부)를 돌며 세대를
        #   심어서 `enable_unpack_cache` 가 꺼 둔 **어텐션 모듈까지 되살렸다.**
        #   어텐션은 층당 1회 호출이라 적중이 0인데 버퍼만 남는다(dense 112.5MB / 타잉 101.3MB).
        #   지금은 **무장된 목록만** 돈다.
        if getattr(self, "_unpack_cache", False):
            self._unpack_gen += 1
            for _m in getattr(self, "_armed_tlinears", ()):
                _m._unpack_gen = self._unpack_gen

        # ★P031: 기본(infer_repeat=1.0)이면 schedule == range(n_layers) 라 종전과 동일하다.
        schedule = self.visit_schedule()
        repeating = len(schedule) != cfg.n_layers
        # ★P049B: 학습 중 반복은 **`train_repeat` 으로만** 허용한다. `infer_repeat` 은 여전히 금지 —
        #   결과 020 이 그 mismatch 를 종결했고, 학습에서 켜면 grad checkpoint 와도 섞인다.
        if repeating and self.training and float(getattr(cfg, "train_repeat", 1.0) or 1.0) == 1.0:
            raise RuntimeError("infer_repeat 는 **추론 전용**이다. 학습 경로에서 켜지 않는다 "
                               "(층 반복은 학습된 깊이 분포 밖이고, grad checkpoint 와도 섞인다). "
                               "학습 시 반복은 --train-repeat 로(P049B).")
        seen = {}                                       # owner -> 그 owner 를 몇 번째 통과 중인가

        # ★★P049 §17.3 — `--reuse-attn-on-dup`. **재귀 통과에서만** 켜진다.
        #   결과 041 §17 이 **복제층 어텐션 출력 cos 0.9882** 를 쟀다 = 두 번째 통과가
        #   거의 같은 것을 다시 계산한다. **연산이 실제로 주는 첫 레버**다.
        #   ⚠️ `repeating` 이 아니면 이 블록 전체가 죽은 코드고 **비트 동일**이다.
        _reuse_attn = bool(getattr(cfg, "reuse_attn_on_dup", False)) and repeating
        if _reuse_attn:
            from collections import Counter
            _visit_total = Counter(schedule)            # 층 인덱스 -> 총 방문 횟수
            _visit_no, _attn_cache = {}, {}
            # ★CLA/어텐션 타잉이면 **남이 내 KV 를 쓴다** — 그런 owner 의 KV 는 못 건너뛴다
            _shared_owner = {self.owner[j] for j in schedule if self.owner[j] != j}

        kv_bank, mode_hist = {}, []
        for step_idx, i in enumerate(schedule):
            layer = self.layers[i]
            mode_p = None
            if cfg.n_modes > 1:
                if mode_override is not None:
                    mp = mode_override[i] if mode_override.dim() == 2 else mode_override
                    mode_p = mp.to(x.dtype).view(1, 1, -1).expand(B, T, -1)
                else:
                    mode_p = F.softmax(self.router(x) + self.router_bias[i], dim=-1)
                mode_hist.append(mode_p)

            # ★★P049 §17.3 — 이 층을 이미 지났으면 **어텐션을 다시 계산하지 않는다.**
            #   ⚠️**KV 블록보다 먼저** 정해야 한다 — KV 계산을 건너뛸지가 여기에 달렸다.
            _ao, _want = None, False
            if _reuse_attn and _visit_total[i] > 1:
                _vn = _visit_no.get(i, 0)
                _visit_no[i] = _vn + 1
                if _vn == 0:
                    _want = True                        # 첫 통과 — 출력을 받아 둔다
                else:
                    _ao = _attn_cache.get(i)            # 두 번째 이후 — 재사용

            # ★캐시 키 — R=1.0 이면 종전처럼 **정수 owner 인덱스**다(비트 동일성 보존).
            #   반복 중이면 같은 owner 를 여러 번 지나므로 (owner, 통과번호) 로 분리한다.
            #   그렇게 안 하면 두 번째 통과가 첫 통과의 KV 를 덮어써서 캐시가 조용히 틀려진다.
            own = self.owner[i]
            if i == own:
                pas = seen.get(own, 0)
                seen[own] = pas + 1
            else:
                pas = seen.get(own, 1) - 1
            key = own if not repeating else (own, pas)

            if i == own and _ao is not None and own not in _shared_owner \
                    and not use_cache and not past_kv:
                # ★★P049 §17.3 — 어텐션 **출력**을 재사용하는 통과에서 이 층이 그 KV 의
                #   **유일한 소비자**면 **KV 계산도 건너뛴다.** 그래야 *"연산이 준다"* 가
                #   실제로 성립한다(출력만 재사용하고 KV 는 계산하면 QKV 사영이 그대로 남는다).
                #   ⚠️`use_cache`/`past_kv` 면 건너뛰지 않는다 — 캐시에 None 이 들어간다.
                kv_bank[key] = None
            elif i == own:
                reuse = repeating and cfg.repeat_kv_reuse and pas > 0
                if reuse:
                    kv_bank[key] = kv_bank[(own, 0)]     # 첫 통과 KV 재사용(대조 조건)
                else:
                    k_new, v_new = layer.attn_mod.compute_kv(x, cos, sin)
                    if past_kv and key in past_kv:
                        k_old, v_old = past_kv[key]
                        # ★P077 단계1 — 저장된 KV 가 낮은 dtype 일 수 있다. **계산 dtype 으로
                        #   되올려서** 잇는다. 그래야 어텐션 산술이 종전과 같다.
                        k_new = torch.cat([k_old.to(k_new.dtype), k_new], dim=2)
                        v_new = torch.cat([v_old.to(v_new.dtype), v_new], dim=2)
                    kv_bank[key] = (k_new, v_new)
            elif key not in kv_bank:
                # ★축소(R^<1)에서 CLA 그룹 경계가 잘리면 owner 가 스케줄에 없을 수 있다.
                #   그때는 이 층이 스스로 KV 를 계산한다(조용한 KeyError 대신 명시적 폴백).
                k_new, v_new = layer.attn_mod.compute_kv(x, cos, sin)
                if past_kv and key in past_kv:
                    k_old, v_old = past_kv[key]
                    k_new = torch.cat([k_old.to(k_new.dtype), k_new], dim=2)   # ★P077 단계1
                    v_new = torch.cat([v_old.to(v_new.dtype), v_new], dim=2)
                kv_bank[key] = (k_new, v_new)
            kv = kv_bank[key]

            if cfg.grad_checkpoint and self.training:
                _out = checkpoint(lambda inp, L=layer, k=kv, mp=mode_p, ao=_ao, wa=_want:
                                  L(inp, k, cos, sin, mp, ao, wa), x, use_reentrant=False)
            else:
                _out = layer(x, kv, cos, sin, mode_p, _ao, _want)
            if _want:
                x, _attn_cache[i] = _out
            else:
                x = _out
            # ★마지막 방문이면 캐시를 버린다 — 안 그러면 유니크 층 수만큼 (B,T,dim) 이 상주한다
            if _reuse_attn and _visit_total[i] > 1 and _visit_no.get(i, 0) >= _visit_total[i]:
                _attn_cache.pop(i, None)

            # ★P034 단계3C — 이 MLP 를 쓰는 연속 구간이 끝나면 **즉시 버퍼를 버린다.**
            #   1차 구현은 이걸 안 해서 dense 가 20층분 fp32 를 들고 40% 느려졌다(§13).
            if getattr(self, "_unpack_cache", False):
                _nxt = schedule[step_idx + 1] if step_idx + 1 < len(schedule) else None
                if _nxt is None or self.layers[_nxt].mlp[0] is not layer.mlp[0]:
                    self._clear_mlp_unpack(layer.mlp[0])

        x = self.norm_f(x) * self.norm_f_scale
        logits = self._head_logits(x)          # ★P034 단계5(청크 복원 포함)

        if use_cache:
            # kv_bank 는 owner 층만 키로 갖는다(§CLA 주의 참조) → 그대로 다음 스텝의 past 가 된다.
            # ★★P077 단계1 (2026-08-30) — **KV 를 저장할 때만 dtype 을 낮춘다.**
            #
            #   왜 여기인가: `--repeat-kv-reuse` 가 기각된 뒤(결과 062) **엔트리 수를 줄이는
            #   길이 닫혔다.** 남은 KV 레버는 **엔트리당 바이트**뿐이다.
            #   fp32 -> bf16 이면 KV 가 정확히 절반이 된다(15.0 -> 7.5 MiB @ seq 1024).
            #
            #   ⚠️★**계산은 손대지 않는다.** 어텐션에 들어가기 직전에 다시 올린다(아래
            #   `_kv_cast_in`). 그래서 이 플래그는 **저장 정밀도만** 바꾼다 — 활성값·
            #   그래디언트·마스터 가중치는 어느 모드에서도 그대로다.
            #   ⚠️**기본 `fp32` 는 캐스팅 자체를 건너뛴다** = 종전 경로와 **비트 동일**.
            _kvd = getattr(cfg, "kv_dtype", "fp32")
            if _kvd != "fp32":
                _dt = {"bf16": torch.bfloat16, "fp16": torch.float16}[_kvd]
                kv_bank = {k: (None if v is None else (v[0].to(_dt), v[1].to(_dt)))
                           for k, v in kv_bank.items()}
            return (logits, kv_bank) if not return_aux else (logits, kv_bank, None)
        if not return_aux:
            return logits
        aux = {"router_loss": self._balance(mode_hist),
               "mode_usage": (torch.stack([p.mean(dim=(0, 1)) for p in mode_hist]).detach()
                              if mode_hist else None)}
        return logits, aux

    def _balance(self, hist):
        if not hist:
            return torch.zeros((), device=self.emb.weight.device)
        loss = 0.0
        for p in hist:
            f = p.mean(dim=(0, 1))
            loss = loss + self.cfg.n_modes * (f * f).sum()
        return loss / len(hist)

    # ---------- optimizer ----------
    def param_groups(self, lr, weight_decay=0.1):
        import math
        tied = {id(p) for m in self.mid_mlps for p in m.parameters()} if self.cfg.tie_mlp else set()
        gt, dense, nodecay, lrm = [], [], [], []
        for n, p in self.named_parameters():
            if not p.requires_grad:
                continue
            # ★★P086 — 승수는 **약한 WD** 를 받는다. 0 이면 대칭성 표류로 노름이
            #   무한히 자란다(논문 §4.1·그림 4) — bf16·삼진에서 양자화 오차가 커진다.
            #   🚫`nodecay`(wd=0) 에 넣으면 안 된다. 그래서 **먼저** 가른다.
            if n.endswith(".lrm"):
                lrm.append(p)
            elif p.dim() < 2 or any(k in n for k in ("scale", "shift", "gates", "gain", "bias")):
                nodecay.append(p)
            elif id(p) in tied:
                gt.append(p)
            else:
                dense.append(p)
        g = self.cfg.mlp_group if self.cfg.tie_mlp else 1
        return [{"params": gt, "lr": lr / math.sqrt(g), "weight_decay": weight_decay},
                {"params": dense, "lr": lr, "weight_decay": weight_decay},
                {"params": nodecay, "lr": lr, "weight_decay": 0.0},
                {"params": lrm, "lr": lr, "weight_decay": 0.01}]   # ★약한 WD(P086)

    # ---------- accounting ----------
    # ★bpw 회계 규약 (2026-07-31 통일 — 결과 016 §7.4·§8.4, P034 §5)
    #   종전 문제: 삼진 1.95 는 "코드 + 그룹스케일 + 컨테이너" 인데 sparse34 1.25 는
    #   **순수 코드공간뿐**이었다. 서로 다른 규약의 두 값으로 비율을 만들어 감축비가
    #   2.66× 로 과대됐다(동일 회계로는 2.11×).
    #
    #   정본 = **안 B(코드 + 그룹 스케일)**. 이유:
    #     ① log2(3) + 16/128 = 1.7100 이 문서의 "g128 삼진 1.71" 과 정확히 일치하고
    #        **설계 시점(가중치가 난수일 때)에 계산 가능한 고정 상수**다.
    #        안 C 로 1.95 를 유지하려면 학습 후에만 아는 실측 엔트로피(1.554)가 필요한데
    #        report() 는 학습 **시작 전**에 호출된다 → 계산 자체가 불가능.
    #     ② 코드와 스케일은 **우리가 반드시 저장해야** 하는 것이다(둘 중 하나만으로는 복원 불가).
    #        컨테이너는 **포맷 선택**의 문제이고 우리는 아직 포맷을 안 정했다.
    #     ③ 논문(Sherry) 기준선 1.67 과 같은 층위 → 외부 비교가 성립한다.
    #   병기 = **안 C(B + 컨테이너)**. 실제 배포 파일 크기 추정용이고 구 문서(30.9MB 계열)와 연속.
    CODE_TERNARY = 1.5849625007211562   # log2(3) — 삼진 심볼 하나의 정보량
    CODE_S34 = 1.25                      # C(4,3)*2^3 = 32 = 2^5, 4가중치당 5비트(무낭비)
    SCALE_BITS = 16.0                    # 그룹 스케일 alpha 를 fp16 로 저장
    CONTAINER_BPW = 0.274                # (안 C 전용) 1.95 - (측정엔트로피 1.554 + 0.125) 역산.
                                         #   GGUF 가정이며 **우리 포맷이 아니다**. 참고값.

    def _bpw(self, container=False):
        """(삼진 bpw, sparse34 bpw, 임베딩 bpw). 규약을 한 곳에서 만든다."""
        scale = self.SCALE_BITS / self.cfg.micro_group
        ovh = self.CONTAINER_BPW if container else 0.0
        b_t = self.CODE_TERNARY + scale + ovh
        b_s = self.CODE_S34 + scale + ovh
        return b_t, b_s, b_t          # 임베딩은 3:4 대상이 아니므로 삼진 규약을 그대로 쓴다

    def mem_breakdown(self, bpw=None, container=False):
        """저장(packed) 메모리의 **정확한** 분해(MB). `report()`·`compare` 의 단일 소스.

        ★ 3:4 준정형(P016)은 **삼진 가중치에만** 적용된다. 임베딩·norm·gate 는 대상이 아니다.
        따라서 "전체 파라미터 × 단일 bpw" 로 근사하면 sparse34 런에서만 과소가 된다.
        이 함수가 그 실수를 원천 차단한다.

        `bpw` 인자는 **구 호출부 호환용**이며 무시된다(규약은 위 상수가 정한다).
        `container=True` 면 안 C(컨테이너 포함) 로 계산한다.
        """
        cfg = self.cfg
        MB = lambda n, b: n * b / 8 / 1024 ** 2
        b_t, b_s, b_e = self._bpw(container)
        bpw_t = b_s if getattr(cfg, "sparse34", False) else b_t
        # ★`weight.numel()` 이 아니라 `weight_numel()` — P034 단계2(latent 해제) 후에도
        #   파라미터 수 회계가 유지된다(해제하면 weight 는 빈 텐서가 된다).
        tern = sum(m.weight_numel() for m in self._tlinears())
        mode = sum(p.numel() for m in self._tlinears() if m.use_mode
                   for p in (m.mode_a, m.mode_b, m.mode_gain))
        emb = self.emb.weight.numel() + (self.emb_up.weight.numel() if self.emb_up is not None else 0)
        lora = sum(p.numel() for m in self.modules() if isinstance(m, LoRA) for p in m.parameters())
        # ★`parameters()` 합에서 빼는 방식은 P034 단계2 후에 **깨진다** — latent 를 해제하면
        #   `parameters()` 합만 줄고 `tern`(=weight_numel)은 그대로라 `other` 가 **음수**가 된다.
        #   그래서 해제분을 되돌려 더한 뒤 뺀다. 해제 전에는 값이 종전과 완전히 같다.
        dropped = sum(m.weight_numel() - m.weight.numel() for m in self._tlinears())
        total_live = sum(p.numel() for p in self.parameters()) + dropped
        other = total_live - tern - mode - emb - lora
        e_bits = b_e if cfg.quantize_embedding else 16
        l_bits = cfg.mlp_lora_bits
        parts = {"ternary": MB(tern, bpw_t), "mode": MB(mode, 16), "emb": MB(emb, e_bits),
                 "other": MB(other, 16), "lora": MB(lora, l_bits)}
        # ★상주(runtime) — 결과 016 실측식: 유니크 삼진 x 4B x 2벌(latent + dequant 사본) + 나머지 fp32
        #   P034 단계2 로 latent 를 해제하면 **1벌**이 된다(= 이 값이 절반 근처로 떨어진다).
        copies = 1 if self.latent_dropped() else 2
        # ★P034 단계3: 삼진 사본이 int8(1바이트) + 그룹 α(fp32, 파라미터당 4/micro_group 바이트)
        if self.lut_stored():
            # ★★P014 단계1 — 코드 1바이트/5가중치 + **행당** alpha 4바이트.
            #   ⚠️`micro_group` 이 식에 **없다** — per-row 이기 때문이다(함정 1 계열:
            #   같은 이름의 항이 경로마다 다른 양을 가리킨다).
            from .lut import packed_bytes as _pb
            _rows = sum(m.out_f for m in self._tlinear_cache)
            tern_bytes = _pb(tern) + _rows * 4
            runtime_mb = (tern_bytes + (mode + lora) * 4 + (emb + other) * 4) / 1024 ** 2
        elif self.int8_stored():
            tern_bytes = tern * (1 + 4 / cfg.micro_group)
            runtime_mb = (tern_bytes + (mode + lora) * 4 + (emb + other) * 4) / 1024 ** 2
        else:
            runtime_mb = ((tern + mode + lora) * 4 * copies + (emb + other) * 4) / 1024 ** 2
        return {"total_mb": sum(parts.values()),          # = packed_mb (구 호출부 호환 별칭)
                "packed_mb": sum(parts.values()),
                "runtime_mb": runtime_mb,
                "runtime_copies": copies,        # 2 = latent + dequant / 1 = P034 단계2 적용
                "int8_stored": self.int8_stored(),   # P034 단계3
                "lut_stored": self.lut_stored(),     # ★P014 단계1
                "latent_dropped": copies == 1,
                "parts_mb": parts,
                "params": {"ternary": tern, "mode": mode, "emb": emb, "other": other, "lora": lora,
                           "total": tern + mode + emb + other + lora},
                "bpw_ternary": bpw_t, "bpw_emb": e_bits,
                "bpw_convention": ("C: code + group scale + container(0.274, GGUF 가정)"
                                   if container else
                                   "B: code(log2 3 / 1.25) + group scale(16/micro_group)"),
                "sparse34": bool(getattr(cfg, "sparse34", False))}

    def kv_report(self, seq_len=1024, kv_bytes=4, repeat=None):
        """★KV 캐시 상주 회계 (REVIEW3 미지 8 / 핸드오프 Q1, 2026-08-29 신설).

        ## 왜 필요한가
        상주식 `유니크삼진 × 4B × 2벌 + 나머지` 에 **KV 캐시가 없다.** 그래서
        `cla_group=1`(KV 소유 층 2배)이나 **재귀**(바퀴마다 K/V 를 따로 든다)의
        진짜 배포 비용을 우리는 몰랐다. 결과 047 §13·059 §13 의 파레토 판정이 여기 걸려 있다.

        ## 무엇을 세나
        `forward` 의 **캐시 키 규약 `(owner, 통과번호)` 를 그대로 복제**해
        **서로 다른 키의 개수**를 센다. 그것이 디코드 중 동시에 살아 있는 K/V 쌍의 수다.

          · `cla_group ^> 1` → 여러 층이 한 owner 를 공유 → 엔트리가 준다
          · 재귀(`train/infer_repeat ^> 1`) → 같은 owner 를 여러 번 지나며 **통과마다 새 엔트리**
          · `repeat_kv_reuse` → 두 번째 이후 통과가 첫 통과 것을 재사용 → 엔트리가 안 는다

        ⚠️**전제**: `use_cache=True` 인 디코드 경로. `reuse_attn_on_dup` 의 KV 생략은
        `use_cache` 에서 발동하지 않으므로 여기서도 세지 않는다.
        ⚠️**seq_len 에 선형**이다 — 한 수가 아니라 **기울기**로 읽는다.

        ★`repeat` 를 주면 **그 배수의 스케줄**로 센다. 🚫**함정 39 대비**: `visit_schedule()` 은
        `model.eval()` 에서 `train_repeat` 을 무시하므로, **재귀로 학습된 체크포인트**는
        호출부가 `repeat=cfg.train_repeat` 를 넘겨야 **자기가 학습된 함수**를 잰다.
        """
        cfg = self.cfg
        schedule = (self._repeat_schedule(float(repeat)) if repeat and float(repeat) != 1.0
                    else self.visit_schedule())
        repeating = len(schedule) != cfg.n_layers
        reuse = bool(getattr(cfg, "repeat_kv_reuse", False))
        seen, keys = {}, []
        for i in schedule:
            own = self.owner[i]
            if i == own:
                pas = seen.get(own, 0)
                seen[own] = pas + 1
            else:
                pas = seen.get(own, 1) - 1
            key = own if not repeating else (own, pas)
            if repeating and reuse and isinstance(key, tuple) and key[1] > 0:
                key = (own, 0)                  # 첫 통과 KV 재사용 = 새 엔트리가 아니다
            keys.append(key)
        entries = len(set(keys))
        per_tok = entries * 2 * cfg.kv_dim * kv_bytes        # K 와 V 두 벌
        return {"kv_entries": entries,
                "kv_visits": len(schedule),
                "kv_dim": cfg.kv_dim,
                "kv_dtype_bytes": kv_bytes,
                "kv_kb_per_token": per_tok / 1024,
                "kv_seq_len": seq_len,
                "kv_mb": per_tok * seq_len / 1024 ** 2}

    def mem_report_all(self, kv_seq_len=1024, kv_bytes=4):
        """정본(B) + 병기(C) + 상주 + ★KV 를 한 번에. trainer 가 json 에 이걸 펼쳐 넣는다.

        ★**`runtime_mb` 는 종전과 같은 값이다**(가중치만) — KV 는 `kv_mb` 로 **따로** 싣는다.
        합치면 기존 런 전부와 비교가 끊긴다(함정 2). 합계가 필요하면 `runtime_plus_kv_mb` 를 읽는다."""
        b = self.mem_breakdown(container=False)
        c = self.mem_breakdown(container=True)
        kv = self.kv_report(seq_len=kv_seq_len, kv_bytes=kv_bytes)
        return {"packed_mb": b["packed_mb"],
                "packed_mb_container": c["packed_mb"],
                "runtime_mb": b["runtime_mb"],
                "runtime_plus_kv_mb": b["runtime_mb"] + kv["kv_mb"],
                "bpw_convention": b["bpw_convention"],
                "bpw_ternary": b["bpw_ternary"],
                "mem_parts_mb": b["parts_mb"],
                "mem_params": b["params"],
                **kv}

    def report(self, bpw=None, l3_mb=32.0):
        cfg = self.cfg
        MB = lambda n, b: n * b / 8 / 1024 ** 2
        bd = self.mem_breakdown()
        bd_c = self.mem_breakdown(container=True)
        tern, mode = bd["params"]["ternary"], bd["params"]["mode"]
        emb, other, lora = bd["params"]["emb"], bd["params"]["other"], bd["params"]["lora"]
        total, mem = bd["params"]["total"], bd["total_mb"]
        bpw_t, e_bits, l_bits = bd["bpw_ternary"], bd["bpw_emb"], cfg.mlp_lora_bits

        per_l = (cfg.dim*cfg.dim*2 + cfg.kv_dim*cfg.dim*2) + 3*cfg.dim*cfg.ffn_dim
        flops = 2 * cfg.n_layers * per_l / 1e9
        # ★2026-08-29 — 종전 `n_kv`/`kv_kb`(owner 만 세고 bf16 가정)는 재귀에서 틀렸다.
        #   정본은 `kv_report()` 로 옮겼다(아래).
        # ★2026-07-31 수정 — `bpw`(함수 인자)를 그대로 쓰고 있었다. 회계 통일 커밋(7b123fc)이
        #   기본값을 `1.95` → `None` 으로 바꾸면서 **이 줄만 따라오지 않아** 모든 학습이
        #   `report()` 에서 죽었다(TypeError: int * NoneType). 정본은 규약이 정한 `bpw_t` 다.
        #   `bpw` 인자는 구 호출부 호환용으로만 남아 있고 무시되는 것이 맞다.
        mlp_mb = MB(3*cfg.dim*cfg.ffn_dim, bpw_t)

        L = []; A = L.append
        A("=" * 72)
        A(f"d={cfg.dim} ffn={cfg.ffn_dim} layers={cfg.n_prelude}+{cfg.n_middle}+{cfg.n_coda}"
          f"  MLP g={cfg.mlp_group if cfg.tie_mlp else 1}  CLA={cfg.cla_group}"
          f"  vocab={cfg.vocab_size} E={cfg.emb_rank or cfg.dim}")
        A("=" * 72)
        _tlbl = '삼진 가중치(3:4 1.25bpw)' if getattr(cfg, "sparse34", False) else '삼진 가중치'
        A(f"  {_tlbl:<24}{tern/1e6:>9.1f}M{MB(tern,bpw_t):>10.1f} MiB")
        if mode: A(f"  {'모드 delta (fp16)':<24}{mode/1e6:>9.1f}M{MB(mode,16):>10.1f} MiB")
        if lora: A(f"  {'LoRA(r='+str(cfg.mlp_lora_rank)+', '+str(l_bits)+'bit)':<24}{lora/1e6:>9.1f}M{MB(lora,l_bits):>10.1f} MiB")
        A(f"  {'임베딩(factorized)':<24}{emb/1e6:>9.1f}M{MB(emb,e_bits):>10.1f} MiB")
        A(f"  {'기타(norm/gate/router)':<24}{other/1e6:>9.1f}M{MB(other,16):>10.1f} MiB")
        A(f"  {'-'*52}")
        A(f"  {'합계':<24}{total/1e6:>9.1f}M{mem:>10.1f} MiB")
        A("")
        A("")
        A(f"  {'저장(packed, 안 B)':<24}{'':>9} {mem:>10.1f} MiB   {bd['bpw_convention']}")
        A(f"  {'저장(참고, 안 C 컨테이너)':<24}{'':>9} {bd_c['packed_mb']:>10.1f} MiB")
        A(f"  {'★상주(runtime, 현 구현)':<24}{'':>9} {bd['runtime_mb']:>10.1f} MiB"
          f"   = 유니크삼진 x 4B x 2벌 + 나머지 fp32 (결과 016)")
        A(f"  L3({l3_mb:.0f}MiB) 상주       : "
          f"{'가능' if bd['runtime_mb'] < l3_mb*0.7 else '불가'}"
          f"   ★**상주 기준**으로 판정한다 — 저장 기준은 {mem:.1f}MB 라 오해를 부른다(결과 016)")
        if cfg.tie_mlp:
            A(f"  타이드 MLP 1그룹      : {mlp_mb:.1f} MiB  ({cfg.mlp_group}회 연속 재사용)")
        else:
            A(f"  MLP 블록(층별 독립)    : {mlp_mb:.1f} MiB  (dense: 재사용 없음)")
        A(f"  토큰당 FLOPs          : {flops:.3f} GFLOP")
        # ★2026-08-29 — 종전 줄은 `owner` 만 세어 **재귀에서 틀렸다**(바퀴마다 K/V 가 따로 산다).
        #   정본은 `kv_report()` 이고, forward 의 키 규약 `(owner, 통과번호)` 를 그대로 복제한다.
        _kv = self.kv_report(seq_len=cfg.max_seq_len)
        A(f"  ★KV 캐시(fp32)        : {_kv['kv_kb_per_token']:.1f} KB/token  "
          f"(엔트리 {_kv['kv_entries']}개 / 방문 {_kv['kv_visits']}회)")
        A(f"                          {cfg.max_seq_len} ctx {_kv['kv_mb']:.1f} MiB "
          f"→ ★상주+KV = {bd['runtime_mb'] + _kv['kv_mb']:.1f} MiB")
        A(f"    ⚠️KV 는 seq 에 선형이다 — 한 수가 아니라 기울기로 읽는다")
        A("=" * 72)
        return "\n".join(L)
