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
def pattern_table(g: int, device=None) -> torch.Tensor:
    """`(3**g, g)` 짜리 **모든 삼진 패턴**. 원소는 {-1,0,1}.

    ⚠️`g` 를 키우면 표가 **3^g 로 폭발**한다. g=4 는 81, g=8 이면 6561.
    **T-MAC 이 g=4 를 쓰는 이유가 이것**이고, 우리도 그렇게 한다.
    """
    assert 1 <= g <= 5, f"g 는 1~5 (3^g 폭발). 받은 값 {g}"
    idx = torch.arange(3 ** g, device=device)
    cols = [((idx // (3 ** k)) % 3) - 1 for k in range(g)]
    return torch.stack(cols, dim=1).to(torch.float32)


def weight_codes(w_tern: torch.Tensor, g: int) -> tuple[torch.Tensor, int]:
    """삼진 가중치 `(O, I)` 를 **g개씩 묶은 패턴 인덱스** `(O, ceil(I/g))` 로.

    ★**이것이 배포 시 디스크에 있는 것**이다 — 값이 아니라 **인덱스**다.
    """
    O, I = w_tern.shape
    pad = (-I) % g
    w = torch.nn.functional.pad(w_tern.to(torch.int64), (0, pad))
    c = (w + 1).reshape(O, -1, g)
    p3 = torch.tensor([3 ** k for k in range(g)], dtype=torch.int64, device=w.device)
    return (c * p3).sum(-1), I + pad


def lut_linear(x: torch.Tensor, codes: torch.Tensor, g: int, i_pad: int,
               alpha: torch.Tensor | None = None, group: int = 0) -> torch.Tensor:
    """★**참조 LUT matmul.** `x (B, I)` · codes `(O, I/g)` -> `(B, O)`.

    `alpha` 는 **그룹 스케일**(`micro_group`). ★**P014B §1.1 의 게이트 U2 가 여기서 답해진다** —
    *"커널이 g128 그룹 스케일을 받는가"*. **우리 구현이므로 받는다.** 외부 커널(BitNet 원형)이
    텐서 스케일만 받는 것과 다르다. **그 차이가 이 파일을 직접 쓰는 이유의 절반**이다.

    🚫**느리다.** 표를 `(B, I/g, 3^g)` 로 통째로 만든다. **정확성과 메모리 증명용**이다.
    """
    B, I = x.shape
    if i_pad > I:
        x = torch.nn.functional.pad(x, (0, i_pad - I))
    P = pattern_table(g, x.device).to(x.dtype)                  # (3^g, g)
    xg = x.reshape(B, -1, g)                                    # (B, J, g)
    lut = torch.einsum("bjg,pg->bjp", xg, P)                    # (B, J, 3^g)
    J = xg.shape[1]
    if alpha is None:
        idx = codes.t().unsqueeze(0).expand(B, J, codes.shape[0])       # (B, J, O)
        return lut.gather(2, idx).sum(1)
    # ★그룹 스케일이 있으면 **묶음 경계마다** 곱한다. group 은 I 축의 원소 수 단위다.
    assert group % g == 0, f"micro_group {group} 이 LUT g {g} 의 배수여야 한다"
    per = group // g                                            # 그룹 하나에 든 LUT 묶음 수
    idx = codes.t().unsqueeze(0).expand(B, J, codes.shape[0])
    part = lut.gather(2, idx)                                   # (B, J, O)
    part = part.reshape(B, -1, per, codes.shape[0]).sum(2)      # (B, n_group, O)
    return (part * alpha.t().unsqueeze(0)).sum(1)


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
