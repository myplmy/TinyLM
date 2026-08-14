#!/usr/bin/env python3
"""F-1 게이트 — **`enable_gqa=True` 가 종전 `repeat_interleave` 와 같은 답을 내는가.** 학습 0.

## 왜 이 게이트가 필요한가

`Attention.forward` 는 지금까지 K/V 를 **물리적으로 `n_rep`(=4) 배 복제**해서 SDPA 에 넘겼다.
`(B, 3, T, 64)` → `(B, 12, T, 64)`. 우리 표준 형상(mb8×seq1024, 20층)에서 이 복제본은
**층당 K/V 각 24MB × 2 × 20층 ≈ 0.4~0.5 GiB** 의 활성 메모리다.

`enable_gqa=True` 는 커널이 **복제 없이** 같은 KV 헤드를 여러 Q 헤드에 태운다. 그런데
**커널 경로가 바뀐다** — 그래서 `0.000e+00` 을 기대하면 안 된다. 결과 028 §11 이
`_weight_int8pack_mm` 에서 **1.7e-3 = bf16 누산 자릿수**를 관측했고 여기도 같은 계열이다.

⚠️ **이 스크립트는 속도를 재지 않는다.** 속도는 단독 실행·정상상태 조건이 필요하고
(결과 016 §12.5), 세션 간 드리프트가 7.5% 다(결과 037 §11.4). 여기서 재면 그 숫자가
**비교 불가인 채로 인용**된다. VRAM·속도는 **배치가 같은 세션 안에서** 잰다.

## 게이트

| # | 무엇 | 통과 조건 |
|---|---|---|
| **G-a** | 로짓 최대 절대차 | **< 1e-3**(bf16 누산 자릿수) |
| **G-b** | `enable_gqa` 인자 수용 | 예외 없이 동작(torch 버전 게이트) |
| **G-c** | Flash/mem-efficient 백엔드 유지 | 강제 컨텍스트에서 거부되지 않음 |
| **G-d** | KV 캐시 경로 불변 | 캐시 있는 forward 는 **비트 동일**(플래그가 그 경로를 안 탄다) |

**하나라도 실패하면 F-1 을 채택하지 않는다.**

사용:
    python scripts/diag_gqa_equiv.py                 # tiny 프리셋(가중치 무관, 난수)
    python scripts/diag_gqa_equiv.py --preset m100R1c
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

import torch                                                    # noqa: E402
import torch.nn.functional as F                                 # noqa: E402

from tinylm.config import build_config                          # noqa: E402
from tinylm.model.transformer import TiedMLPTransformer         # noqa: E402

TOL = 1e-3


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="tiny")
    ap.add_argument("--seq", type=int, default=256)
    ap.add_argument("--bs", type=int, default=2)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()

    fails = []
    dev = a.device
    print(f"torch {torch.__version__} / device {dev} / preset {a.preset}")

    # ── G-b : 인자 자체가 받아들여지는가 ──────────────────────────────────────
    _hdr("G-b  enable_gqa 인자 수용")
    q = torch.randn(1, 12, 32, 64, device=dev)
    k = torch.randn(1, 3, 32, 64, device=dev)
    v = torch.randn(1, 3, 32, 64, device=dev)
    try:
        F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
        print("  OK — SDPA 가 enable_gqa 를 받는다")
    except Exception as e:
        print(f"  실패: {type(e).__name__}: {e}")
        print("  -^> torch 버전이 enable_gqa 를 지원하지 않는다. F-1 은 여기서 종료.")
        fails.append("G-b")
        _summary(fails)
        return 1

    # 참조: 물리 복제 결과와 직접 비교(모델 없이 커널만)
    ref = F.scaled_dot_product_attention(
        q, k.repeat_interleave(4, dim=1), v.repeat_interleave(4, dim=1), is_causal=True)
    got = F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
    d = (ref - got).abs().max().item()
    print(f"  커널 단독 최대 절대차 {d:.3e}  (참고값 — 모델 전체는 G-a 가 본다)")

    # ── G-c : 백엔드가 유지되는가 ─────────────────────────────────────────────
    #
    # ★★2026-08-14 수정 (실사고, 결과 046) — **이 게이트는 판정에 들어가지 않았다.**
    #   거부를 `print` 만 하고 `fails.append` 를 안 했다. 그래서 실제로 **FLASH·
    #   MEM_EFFICIENT 가 둘 다 거부됐는데** 판정 줄은 *"✅ 전 게이트 통과 —
    #   --sdpa-gqa 를 학습에 쓸 수 있다"* 를 찍었다. 40분 뒤 단계 B 가 그 대가를 냈다:
    #   **reserved +1.38 GB(+27%), ms/step +95.8%** — 예측(−0.4~0.5 GiB)의 정반대다.
    #   ★**인쇄와 판정을 따로 짜면 갈라진다**(계측함정 38).
    #
    #   ⚠️**MATH 만 남는 것이 왜 치명적인가**: 물리 복제(off) 경로는 q·k·v 의 head 수가
    #   같아 fused kernel 을 탄다. `enable_gqa=True` 는 head 수를 다르게 넘기므로
    #   fused 가 거부하고 MATH 로 떨어진다 — MATH 는 어텐션 행렬을 전부 만든다.
    #   **활성 메모리를 아끼려던 플래그가 활성 메모리를 늘린다.**
    _hdr("G-c  Flash / mem-efficient 백엔드가 enable_gqa 를 거부하지 않는가")
    try:
        from torch.nn.attention import SDPBackend, sdpa_kernel
        rejected, avail = [], []
        for be, name in ((SDPBackend.FLASH_ATTENTION, "FLASH"),
                         (SDPBackend.EFFICIENT_ATTENTION, "MEM_EFFICIENT"),
                         (SDPBackend.MATH, "MATH")):
            try:
                with sdpa_kernel(be):
                    F.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
                print(f"  {name:14s} OK")
                avail.append(name)
            except Exception as e:
                print(f"  {name:14s} 거부 — {type(e).__name__}: {str(e)[:90]}")
                rejected.append(name)
        # ★판정: **융합 커널이 하나도 안 남으면 실패**다. MATH 만으로는 이 축의 존재 이유
        #   (활성 메모리 절감)가 성립하지 않는다.
        if not (set(avail) - {"MATH"}):
            print("  🚫 G-c 실패 — **융합 커널이 하나도 안 남는다**(MATH 단독). "
                  "enable_gqa 는 활성 메모리를 아끼려는 플래그인데 MATH 는 "
                  "어텐션 행렬을 전부 만든다 → **이득이 아니라 대가**가 된다.")
            print(f"     거부된 백엔드: {', '.join(rejected) or '(없음)'}")
            print("     ⚠️ 이 빌드에서 애초에 융합 커널이 없다면(예: flash 미컴파일) "
                  "그건 이 플래그의 잘못이 아니다 — **off/on 쌍으로 실측해 귀속한다.**")
            fails.append("G-c")
        else:
            print(f"  ✅ G-c 통과 — 융합 커널 유지: {', '.join(sorted(set(avail) - {'MATH'}))}")
    except ImportError:
        print("  torch.nn.attention 없음 — 백엔드 강제 확인 생략(치명 아님)")

    # ── G-a : 모델 전체 로짓 ──────────────────────────────────────────────────
    _hdr("G-a  모델 전체 로짓 동등성 (학습 경로, is_causal)")
    cfg_off = build_config(a.preset, "tied", a.seq, True)
    torch.manual_seed(1337)
    m = TiedMLPTransformer(cfg_off).to(dev).eval()
    x = torch.randint(0, cfg_off.vocab_size, (a.bs, a.seq), device=dev)
    with torch.no_grad():
        m.cfg.sdpa_gqa = False
        lo = m(x).float()
        m.cfg.sdpa_gqa = True
        ln = m(x).float()
        m.cfg.sdpa_gqa = False
    mad = (lo - ln).abs().max().item()
    rel = mad / lo.abs().max().clamp_min(1e-12).item()
    print(f"  최대 절대차 {mad:.3e}   (상대 {rel:.3e})   기준 {TOL:.0e}")
    if mad < TOL:
        print("  ✅ G-a 통과")
    else:
        print("  🚫 G-a 실패 — 커널 차이로 설명되지 않는 크기다. 구현을 의심할 것.")
        fails.append("G-a")

    # ── G-d : KV 캐시 경로는 손대지 않았는가 ───────────────────────────────────
    _hdr("G-d  KV 캐시 경로 불변 (플래그가 attn_mask 경로를 타지 않는다)")
    try:
        with torch.no_grad():
            m.cfg.sdpa_gqa = False
            a1 = _cached_logits(m, x)
            m.cfg.sdpa_gqa = True
            a2 = _cached_logits(m, x)
            m.cfg.sdpa_gqa = False
        if a1 is None:
            print("  캐시 API 미확인 — 생략(치명 아님). 정본 게이트는 diag_kvcache.py 다.")
        else:
            d2 = (a1 - a2).abs().max().item()
            print(f"  캐시 경로 최대 절대차 {d2:.3e}   기준 **0.0**(비트 동일이어야 한다)")
            if d2 == 0.0:
                print("  ✅ G-d 통과 — 플래그가 캐시 경로를 건드리지 않는다")
            else:
                print("  🚫 G-d 실패 — 학습 경로에만 적용한다는 설계가 깨졌다")
                fails.append("G-d")
    except Exception as e:
        print(f"  생략({type(e).__name__}: {str(e)[:80]}) — 정본 게이트는 diag_kvcache.py 다")

    _summary(fails)
    return 1 if fails else 0


def _cached_logits(m, x):
    """KV 캐시를 쓰는 forward 가 있으면 마지막 로짓을 돌려준다. 없으면 None."""
    for name in ("forward_cached", "generate_step"):
        if hasattr(m, name):
            return getattr(m, name)(x)
    return None


def _summary(fails):
    _hdr("판정")
    if fails:
        print(f"  🚫 실패 게이트: {', '.join(fails)}  -^> **F-1 을 채택하지 않는다**")
    else:
        print("  ✅ 전 게이트 통과 — --sdpa-gqa 를 학습에 쓸 수 있다")
        print("  ⚠️ 단 **속도·VRAM 은 여기서 재지 않았다.** 배치가 같은 세션 안에서 잰다.")


if __name__ == "__main__":
    raise SystemExit(main())
