"""★★P014 단계0 — **LUT 커널의 참조 구현.** (2026-08-22 사용자 지시로 착수)

## 왜 이것이 필요한가 — 결과 052 가 강제했다

결과 052 의 결정적 산술:

| 경로 | 상주(MiB) | 40 MiB 목표 |
|---|---:|---|
| fp32 | 451.5 | 🚫 |
| drop-latent | 242.2 | 🚫 |
| **+ int8 삼진** | **86.9** | 🚫 |
| int8 + 임베딩 ternary | **39.5** | ⚠️**아슬** |
| ★**LUT + 임베딩 int8** | ★**18.3** | ✅ |

★**int8 로는 목표에 못 간다.** int8 은 가중치당 **8비트**인데 삼진의 이론값은 **log2(3)=1.585비트**다.
**5.05배를 버리고 있다.** 그것을 회수하는 유일한 길이 **패킹된 채로 계산하는 커널**이고,
그 커널의 표준 구조가 **LUT(T-MAC 계열)** 다.

## ★이 파일이 하는 것과 **하지 않는 것**

| | |
|---|---|
| ✅**한다** | 삼진 **패킹 포맷**(5트릿/바이트 = **1.6 bpw**) · 무손실 왕복 · **참조 LUT matmul** · 바이트 회계 |
| 🚫**안 한다** | ★**속도.** 이 구현은 **느리다.** PyTorch 로 쓴 참조이고 **정확성과 메모리만** 증명한다 |

> ★★**왜 느린 것을 먼저 쓰는가** — P014B §1.1 의 게이트 U1(*"우리 dim 768 에서 LUT 가 이득인가"*)은
> **실제 커널이 있어야 답한다.** 그러나 **U2(그룹 스케일을 받는가)와 메모리 이득은 지금 답할 수 있고**,
> ★**그 둘이 부정이면 빠른 커널을 써도 소용이 없다.** 값싼 것부터 닫는다.
>
> ⚠️★**그리고 "LUT 로 18.3 MiB" 는 아직 계산값이다.** 이 파일의 `packed_bytes()` 가
> **실측으로 바꾼다.** 함정 1(저장 ≠ 상주)을 여기서도 지킨다 — 아래는 **저장(packed)** 이다.

## 포맷 — **5트릿/바이트**

    트릿 t in {-1,0,1}  ->  코드 c = t+1 in {0,1,2}
    바이트 = c0 + 3*c1 + 9*c2 + 27*c3 + 81*c4      (최대 242 < 256)
    = 8비트 / 5가중치 = **1.6 bpw**

★**3:4 준정형(`sparse34`, 1.25bpw)보다 크다.** 그건 다른 축이고 **섞지 않는다**(함정 28).
⚠️**이론 하한 log2(3)=1.585 에 대해 우리 포맷은 1.6 — 낭비 0.95%.**
**더 줄이려면 트릿 수를 늘려야 하는데**(예: 8트릿=6561>2^12) **바이트 정렬이 깨진다.**

## LUT matmul 구조 (T-MAC 계열)

    입력 x (B, I) 를 g개씩 묶는다        ->  (B, I/g, g)
    3^g 개 패턴 P (3^g, g), 원소 in {-1,0,1}
    표    lut[b, j, p] = sum_k P[p,k] * x[b, j*g+k]      <- **활성값으로 표를 만든다**
    출력  y[b, o]      = sum_j lut[b, j, code[o, j]]     <- **가중치는 인덱스일 뿐**

★★**핵심은 "표를 활성값으로 만들고 가중치로 인덱싱한다" 는 것**이다.
그래서 **가중치는 곱셈에 한 번도 안 들어가고 패킹된 채로 있어도 된다.**
"""
from __future__ import annotations

import torch

TRITS_PER_BYTE = 5
_POW3 = (1, 3, 9, 27, 81)


# ─────────────────────────────────────────────────────────── 패킹
def pack_trits(t: torch.Tensor) -> tuple[torch.Tensor, int]:
    """`t` 는 마지막 축이 가중치인 **{-1,0,1} 텐서**. `(packed_uint8, n_orig)` 를 돌려준다.

    ⚠️**입력 검증을 한다.** 삼진이 아닌 값이 들어오면 **조용히 반올림하지 않고 죽인다** —
    조용한 반올림은 *"패킹이 손실적이다"* 라는 잘못된 결론을 만든다(함정 31 계열).
    """
    assert t.dtype in (torch.int8, torch.int16, torch.int32, torch.int64, torch.float32), \
        f"삼진 텐서여야 한다: dtype={t.dtype}"
    ti = t.to(torch.int64)
    assert bool(((ti >= -1) & (ti <= 1)).all()), "값이 {-1,0,1} 밖이다 — 이건 삼진이 아니다"
    n = ti.shape[-1]
    pad = (-n) % TRITS_PER_BYTE
    if pad:
        ti = torch.nn.functional.pad(ti, (0, pad))          # 0 = 코드 1 이 아니라 트릿 0
    c = (ti + 1).reshape(*ti.shape[:-1], -1, TRITS_PER_BYTE)   # {0,1,2}
    w = torch.tensor(_POW3, dtype=torch.int64, device=t.device)
    b = (c * w).sum(-1)
    assert bool((b < 256).all()), "패킹값이 255 를 넘었다 — 포맷이 깨졌다"
    return b.to(torch.uint8), n


def unpack_trits(b: torch.Tensor, n: int) -> torch.Tensor:
    """`pack_trits` 의 역. `n` 은 패딩 전 원래 길이."""
    x = b.to(torch.int64)
    out = []
    for k in range(TRITS_PER_BYTE):
        out.append((x // _POW3[k]) % 3)
    c = torch.stack(out, dim=-1).reshape(*b.shape[:-1], -1)
    return (c[..., :n] - 1).to(torch.int8)


def packed_bytes(n_weights: int) -> int:
    """★**저장(packed) 바이트.** 함정 1 — 이것은 상주가 아니다."""
    return (n_weights + TRITS_PER_BYTE - 1) // TRITS_PER_BYTE


def bpw() -> float:
    return 8.0 / TRITS_PER_BYTE


# ─────────────────────────────────────────────────────── LUT matmul
def pattern_table(g: int, device=None, dtype=None):
    """`(3**g, g)` 짜리 **모든 삼진 패턴**. 원소는 {-1,0,1}.

    ⚠️`g` 를 키우면 표가 **3^g 로 폭발**한다. g=4 는 81, g=5 는 243, g=6 이면 729.

    ★★**우리는 g=5 를 쓴다** — T-MAC 이 g=4 인 것과 다르고, **그것이 이 구현의 핵심 설계**다:

        5트릿 = 1바이트 (코드 0~242 < 256)  ->  ★**패킹된 바이트가 곧 LUT 인덱스**다

    g=4 면 패킹(5트릿/바이트)과 인덱싱(4트릿/그룹)이 **어긋나서** 커널이 매번 비트를
    풀어야 한다. g=5 면 **언팩이 아예 없다.** 표가 3배(81->243) 커지지만 표는
    **활성값당 한 번** 만들고 **출력 채널 전체가 재사용**하므로 실질 비용이 아니다.
    ★**1.600 bpw 와 언팩 0 을 동시에 얻는다.**
    """
    assert 1 <= g <= 6, f"g 는 1~6 (3^g 폭발). 받은 값 {g}"
    idx = torch.arange(3 ** g, device=device)
    cols = [((idx // (3 ** k)) % 3) - 1 for k in range(g)]
    return torch.stack(cols, dim=1).to(dtype or torch.float32)


def weight_codes(w_tern: torch.Tensor, g: int = TRITS_PER_BYTE):
    """삼진 가중치 `(O, I)` 를 **g개씩 묶은 패턴 인덱스** `(O, ceil(I/g))` 로.

    ★**g=5 면 이 결과가 그대로 `pack_trits` 의 출력과 같다** — uint8 한 바이트가
    한 그룹이고 그 값이 LUT 인덱스다. **저장과 인덱싱이 같은 것**이 되는 지점이다.
    ★배포 시 디스크에 있는 것은 **값이 아니라 인덱스**다.
    """
    O, I = w_tern.shape
    pad = (-I) % g
    w = torch.nn.functional.pad(w_tern.to(torch.int64), (0, pad))
    c = (w + 1).reshape(O, -1, g)
    p3 = torch.tensor([3 ** k for k in range(g)], dtype=torch.int64, device=w.device)
    codes = (c * p3).sum(-1)
    dt = torch.uint8 if 3 ** g <= 256 else torch.int16
    return codes.to(dt), I + pad


def lut_linear(x: torch.Tensor, codes: torch.Tensor, g: int, i_pad: int,
               alpha: torch.Tensor | None = None, group: int = 0,
               out_chunk: int = 0) -> torch.Tensor:
    """★★**LUT matmul.** `x (..., I)` · codes `(O, I/g)` -> `(..., O)`.

    `alpha` 는 **그룹 스케일**(`micro_group`). ★**P014B §1.1 의 게이트 U2 가 여기서 답해진다** —
    *"커널이 g128 그룹 스케일을 받는가"*. **우리 구현이므로 받는다.**

    ## ★메모리 — `out_chunk` 가 이 함수의 실용성을 정한다

    표를 만드는 비용은 `B x J x 3^g` 로 작다(B=1, I=768, g=5 -> 154 x 243 = 37K).
    ⚠️★**큰 것은 gather 결과** `(B, J, O)` 다 — B=8·J=154·O=2048 이면 fp32 **10 MB**.
    `out_chunk` 로 **출력 채널을 나눠** 그 텐서를 잘게 만든다. **수학적으로 동일**하다
    (출력 채널끼리 독립이다). 기본 0 = 한 번에.

    ## 🚫**속도에 대한 정직한 말**

    이 구현은 **PyTorch 수준**이고 **GPU 에서 cuBLAS 를 못 이긴다.** 이길 수 없는 이유는
    구현이 나빠서가 아니라 **gather 가 GEMM 보다 메모리 대역을 더 쓰기** 때문이다.
    ★**이 경로의 값어치는 상주 메모리**다 — 우리 목적함수가 그것이다(`CLAUDE.md` 첫 줄).
    속도는 **CPU 배포**에서 `_wq_from_i8()` 의 fp32 복원(층당 2.1~2.2ms)을 없애는 것으로
    갚는다. **그 측정은 P014B 가 소유한다.**
    """
    shp = x.shape
    x2 = x.reshape(-1, shp[-1])
    B, I = x2.shape
    if i_pad > I:
        x2 = torch.nn.functional.pad(x2, (0, i_pad - I))
    P = pattern_table(g, x2.device, x2.dtype)                   # (3^g, g)
    lut = torch.einsum("bjg,pg->bjp", x2.reshape(B, -1, g), P)  # (B, J, 3^g)
    J, O = lut.shape[1], codes.shape[0]
    ci = codes.to(torch.int64)

    # ★★α 규약 — **여기가 이 설계의 유일한 제약**이고 숨기지 않는다.
    #
    #   g=5 는 "패킹된 바이트 = LUT 인덱스" 를 주는 대신 **α 그룹이 5의 배수**여야 한다.
    #   🚫**우리 I=768 = 2^8 x 3 에는 5의 배수인 약수가 없다.** 그러므로 g=5 에서
    #   그룹 α(`micro_group 128`)는 **원리적으로 불가능**하다.
    #
    #   ✅**per-row α 는 된다** — 행 전체가 한 스케일이므로 그룹 경계 문제가 없다.
    #   ★그리고 그 대가는 **이미 측정돼 있다**: 결과 028 per-row **+0.0038~0.0068 bpb**,
    #   실무 분해능 0.008 **미만**. `_fused_int8_linear` 도 **똑같이 per-row 를 요구**한다
    #   (`P014C 단계2`). ★**두 고속 경로가 같은 제약을 갖는 것은 우연이 아니다** —
    #   행당 스케일 하나여야 커널이 누산 뒤에 한 번만 곱할 수 있다.
    per_row = alpha is not None and alpha.shape[-1] == 1
    if alpha is not None and not per_row:
        assert group % g == 0, (
            f"★LUT g={g} 에서 그룹 α 는 group % {g} == 0 을 요구한다(받은 값 {group}). "
            f"🚫**I=768 에는 5의 배수 약수가 없으므로 g=5 + 그룹 α 는 불가능**하다. "
            f"★`--micro-group 0`(per-row)을 쓰세요 — 대가는 결과 028 이 이미 쟀다"
            f"(+0.0038~0.0068 bpb, 분해능 0.008 미만).")

    def _slice(o0, o1):
        idx = ci[o0:o1].t().unsqueeze(0).expand(B, J, o1 - o0)   # (B, J, o)
        part = lut.gather(2, idx).sum(1)                         # (B, o)  <- J 를 먼저 접는다
        if alpha is None:
            return part
        if per_row:
            return part * alpha[o0:o1, 0].unsqueeze(0)
        # 그룹 α: J 를 접기 전에 그룹 단위로 나눠야 한다
        pt = lut.gather(2, idx)
        per = group // g
        return (pt.reshape(B, -1, per, o1 - o0).sum(2)
                * alpha[o0:o1].t().unsqueeze(0)).sum(1)
    step = out_chunk if out_chunk and out_chunk < O else O
    ys = [_slice(o, min(o + step, O)) for o in range(0, O, step)]
    y = ys[0] if len(ys) == 1 else torch.cat(ys, dim=1)
    return y.reshape(*shp[:-1], O)


def residency_bytes(n_unique_ternary: int, n_other_params: int,
                    other_bytes_per: int = 4, n_groups: int = 0) -> dict:
    """★**상주(runtime) 회계.** 함정 1 — `packed_bytes` 와 **다른 양**이다.

    LUT 경로의 상주 = **패킹된 코드 + 그룹 α(fp32) + 나머지 파라미터**.
    ★**latent 한 벌도, dequant 사본도 없다** — 그것이 int8 경로(가중치당 8비트)와의 차이다.
    """
    code = packed_bytes(n_unique_ternary)
    a = n_groups * 4
    other = n_other_params * other_bytes_per
    return {"codes_MiB": code / 2 ** 20, "alpha_MiB": a / 2 ** 20,
            "other_MiB": other / 2 ** 20, "total_MiB": (code + a + other) / 2 ** 20,
            "bpw_effective": (code + a) * 8 / max(n_unique_ternary, 1)}
