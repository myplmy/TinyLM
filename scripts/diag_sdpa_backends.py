#!/usr/bin/env python3
"""P060 단계 A2 — **이 빌드에서 SDPA 백엔드가 무엇이 살아 있는가.** 학습 0 · 수 초.

## 왜 필요한가 — **단계 A 가 기준선을 안 쟀다**

결과 046 의 단계 A(`diag_gqa_equiv.py`)는 **`enable_gqa=True` 로만** 백엔드를 찔렀다.
FLASH·MEM_EFFICIENT 가 거부됐는데 **`enable_gqa=False` 로는 안 찔러 봤다.**
그래서 **거부의 원인을 귀속할 수 없다**:

| 가능성 | 뜻 | 처방 |
|---|---|---|
| (a) 이 빌드에 **융합 커널이 아예 없다** | `enable_gqa` 무관 | **torch 빌드를 바꿔야 한다** |
| (b) 융합 커널은 있는데 **`enable_gqa` 만 못 받는다** | 플래그의 한계 | `enable_gqa` 를 안 쓰면 된다(= 종전 경로) |

**(a)와 (b)는 처방이 완전히 다르다.** 이 도구가 그것을 가른다.

## 무엇을 보는가 — **2 × 4 행렬**

`enable_gqa` **off/on** × 백엔드 **FLASH / MEM_EFFICIENT / CUDNN / MATH**.

- **off** 팔은 K/V 를 물리 복제해 head 수를 맞춘다 = **우리 학습 경로 그대로**
- **on** 팔은 head 수가 다른 채로 넘긴다 = `--sdpa-gqa`

## 성공 기준값 (참고값 — 결과 전에 적는다)

| 무엇이 보이면 | 뜻 |
|---|---|
| off 에서 **FLASH 또는 MEM_EFFICIENT 가 OK** | 융합 커널이 **있다** → 위 (b). 종전 경로는 건강하다 |
| off 에서도 **MATH 만** OK | 위 (a). ★**우리 학습 전체가 MATH 로 돌고 있다** — 그건 F-1 보다 큰 문제다 |
| on 에서만 거부 | `enable_gqa` 미지원 확정 → 결과 046 의 귀속이 완성된다 |

⚠️**이 도구는 품질을 재지 않는다.** 커널 가용성과 상대 속도만 본다.

사용:
    python scripts/diag_sdpa_backends.py
    python scripts/diag_sdpa_backends.py --seq 1024 --bs 8
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch                                                     # noqa: E402
import torch.nn.functional as F                                  # noqa: E402


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def _flag(name):
    fn = getattr(torch.backends.cuda, name, None)
    if fn is None:
        return "(없음)"
    try:
        return str(fn())
    except Exception as e:                                       # noqa: BLE001
        return f"(오류 {type(e).__name__})"


def main():
    ap = argparse.ArgumentParser(description="SDPA 백엔드 가용성 행렬 (학습 0)")
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--q-heads", type=int, default=12)
    ap.add_argument("--kv-heads", type=int, default=3)
    ap.add_argument("--head-dim", type=int, default=64)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--iters", type=int, default=20)
    a = ap.parse_args()
    dev = a.device

    _hdr("환경")
    print(f"  torch {torch.__version__}  device {dev}")
    if dev == "cuda":
        print(f"  gpu   {torch.cuda.get_device_name(0)}  "
              f"capability {torch.cuda.get_device_capability(0)}")
    for f in ("flash_sdp_enabled", "mem_efficient_sdp_enabled",
              "math_sdp_enabled", "cudnn_sdp_enabled"):
        print(f"  torch.backends.cuda.{f:<28} = {_flag(f)}")
    for f in ("is_flash_attention_available", "can_use_flash_attention"):
        if hasattr(torch.backends.cuda, f):
            print(f"  torch.backends.cuda.{f:<28} = (존재)")
    print("  ⚠️ 위 플래그는 **허용 여부**이지 **컴파일 여부**가 아니다. "
          "행렬이 실제 가용성을 본다.")

    B, T, hd = a.bs, a.seq, a.head_dim
    nq, nkv = a.q_heads, a.kv_heads
    n_rep = nq // nkv
    dt = torch.bfloat16 if dev == "cuda" else torch.float32
    q = torch.randn(B, nq, T, hd, device=dev, dtype=dt)
    k0 = torch.randn(B, nkv, T, hd, device=dev, dtype=dt)
    v0 = torch.randn(B, nkv, T, hd, device=dev, dtype=dt)
    k_rep = k0.repeat_interleave(n_rep, dim=1)
    v_rep = v0.repeat_interleave(n_rep, dim=1)

    print(f"\n  형상 q {tuple(q.shape)}  kv {tuple(k0.shape)}  n_rep {n_rep}  dtype {dt}")
    print(f"  off 팔 = K/V 물리 복제 {tuple(k_rep.shape)} (**우리 학습 경로 그대로**)")

    try:
        from torch.nn.attention import SDPBackend, sdpa_kernel
    except ImportError:
        print("\n  🚫 `torch.nn.attention` 이 없다 — 이 torch 는 백엔드 강제를 지원하지 않는다")
        return 1

    backends = [("FLASH", getattr(SDPBackend, "FLASH_ATTENTION", None)),
                ("MEM_EFFICIENT", getattr(SDPBackend, "EFFICIENT_ATTENTION", None)),
                ("CUDNN", getattr(SDPBackend, "CUDNN_ATTENTION", None)),
                ("MATH", getattr(SDPBackend, "MATH", None))]

    def _call(gqa):
        if gqa:
            return F.scaled_dot_product_attention(q, k0, v0, is_causal=True, enable_gqa=True)
        return F.scaled_dot_product_attention(q, k_rep, v_rep, is_causal=True)

    _hdr("★백엔드 가용성 행렬  (off = 물리 복제 / on = enable_gqa)")
    print(f"  {'백엔드':<16}{'off(복제)':<34}{'on(enable_gqa)':<34}")
    print("  " + "-" * 74)
    avail = {False: [], True: []}
    for name, be in backends:
        cells = []
        for gqa in (False, True):
            if be is None:
                cells.append("(이 torch 에 없음)")
                continue
            try:
                with sdpa_kernel(be):
                    _call(gqa)
                cells.append("OK")
                avail[gqa].append(name)
            except Exception as e:                               # noqa: BLE001
                msg = str(e).split("\n")[0][:30]
                cells.append(f"거부 {msg}")
        print(f"  {name:<16}{cells[0]:<34}{cells[1]:<34}")

    _hdr("기본 디스패치 속도 (백엔드 강제 없음)")
    res = {}
    for gqa, lbl in ((False, "off(복제)"), (True, "on(enable_gqa)")):
        try:
            for _ in range(3):
                _call(gqa)
            if dev == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            for _ in range(a.iters):
                _call(gqa)
            if dev == "cuda":
                torch.cuda.synchronize()
            ms = (time.perf_counter() - t0) * 1000 / a.iters
            res[gqa] = ms
            print(f"  {lbl:<18} {ms:8.3f} ms / 호출")
        except Exception as e:                                   # noqa: BLE001
            print(f"  {lbl:<18} 🚫 {type(e).__name__}: {str(e)[:60]}")
    if len(res) == 2 and res[False] > 0:
        print(f"\n  ★on / off = {res[True] / res[False]:.3f}배  "
              f"(결과 046 의 학습 전체 ms/step 비는 1.958배였다)")

    _hdr("판정")
    fused_off = [x for x in avail[False] if x != "MATH"]
    fused_on = [x for x in avail[True] if x != "MATH"]
    if fused_off:
        print(f"  ✅ **off 경로에 융합 커널이 있다**: {', '.join(fused_off)}")
        print("     -^> 우리 학습 경로는 건강하다. 결과 046 의 대가는 **enable_gqa 의 한계**다(가능성 b).")
        if not fused_on:
            print("  🚫 **on 경로에는 융합 커널이 하나도 없다** -^> `--sdpa-gqa` 는 MATH 강제.")
            print("     -^> **결과 046 의 귀속이 완성됐다.** 코드가 아니라 커널 지원의 문제다.")
        else:
            print(f"  ⚠️ on 에도 융합이 있다: {', '.join(fused_on)} — "
                  f"그렇다면 결과 046 의 대가는 **다른 원인**이다. 재조사할 것.")
    else:
        print("  🚫🚫 **off 경로에도 융합 커널이 없다 — MATH 단독이다.**")
        print("     -^> ★이건 F-1 보다 큰 문제다. **우리 학습 전체가 MATH 로 돌고 있다**는 뜻이고,")
        print("        어텐션 활성 메모리·속도의 상당 부분이 그것으로 설명될 수 있다.")
        print("        → torch 빌드 교체를 별도 과제로 올린다(가능성 a).")
    print("\n  ⚠️ 이 도구는 **커널 가용성과 상대 속도**만 본다. 품질·정확성은 "
          "`diag_gqa_equiv.py` 의 G-a 가 본다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
