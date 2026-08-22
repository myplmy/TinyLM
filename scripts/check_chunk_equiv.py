#!/usr/bin/env python3
"""★★P071 — **손실 청킹이 등가인가.** 학습 0 · GPU 0. json 만 읽는다.

## 성공 기준값 (결과보다 먼저 인쇄한다 — 함정 34)

| # | 게이트 | 기준 |
|---|---|---|
| ★**E1** | `ce_c0` 의 `final.val_loss` == `sm_base` | ★**완전 일치**(근사 아님) |
| **E2** | `ce_c64` vs `ce_c0` 상대차 | < **1e-5** |
| **E3** | `ce_c16` vs `ce_c64` | < **1e-5** |
| ★**E4** | `kd_c64` vs `kd_c0` | < **1e-5** — ★**2차 정정이 되돌린 것을 증명** |
| **E5** | NaN/Inf 없음 | `grad_max` 유한 |

★**E1 을 "완전 일치" 로 잡는 이유**: `chunk<=0` 분기는 **문자 그대로 같은 호출**이다.
**근사적으로 같으면 안 되고 같아야 한다.** 다르면 분기를 잘못 짠 것이다.

⚠️**`sm_base` 가 없으면 E1 을 건너뛴다** — 스모크를 먼저 돌려야 한다. 건너뛴 것은
**통과가 아니라 미평가**로 센다(함정 38: 인쇄와 판정이 갈라지면 미탐이 더 비싸다).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "runs" / "logs"


def load(tag):
    """태그로 끝나는 tiny 로그 하나. 없으면 None."""
    hits = sorted(LOGS.glob(f"tiny_*_{tag}.json"))
    if not hits:
        return None
    return json.loads(hits[-1].read_text(encoding="utf-8"))


def val(d):
    f = d.get("final") or {}
    return f.get("val_loss")


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-12)


def main():
    print("#" * 96)
    print("  ★P071 — 손실 청킹 등가성. **기준값을 결과보다 먼저 인쇄한다**(함정 34)")
    print("#" * 96)
    print("  E1 ce_c0 == sm_base        기준: ★**완전 일치**(근사 아님)")
    print("  E2 ce_c64 vs ce_c0         기준: 상대차 < 1e-5")
    print("  E3 ce_c16 vs ce_c64        기준: 상대차 < 1e-5")
    print("  E4 kd_c64 vs kd_c0         기준: 상대차 < 1e-5  ★2차 정정 증명")
    print("  E5 NaN/Inf 없음            기준: grad_max 유한")
    print("\n  ⚠️★건너뛴 게이트는 **통과가 아니라 미평가**로 센다(함정 38).")

    tags = ["sm_base", "ce_c0", "ce_c64", "ce_c16", "kd_c0", "kd_c64"]
    d = {t: load(t) for t in tags}
    print(f"\n{'=' * 96}\n  로드")
    for t in tags:
        v = val(d[t]) if d[t] else None
        print(f"  {'✅' if d[t] else '🚫'} {t:<10} val_loss = "
              f"{v if v is None else f'{v:.10f}'}"
              + ("" if d[t] else "   ← json 없음"))

    fails, skips = [], []

    def gate(name, a, b, exact=False):
        if d.get(a) is None or d.get(b) is None:
            skips.append(f"{name}: {a} 또는 {b} 의 json 이 없다")
            return
        va, vb = val(d[a]), val(d[b])
        if va is None or vb is None:
            skips.append(f"{name}: final.val_loss 가 없다")
            return
        if exact:
            ok = (va == vb)
            print(f"  {'✅' if ok else '🚫'} {name}  {a}={va:.10f}  {b}={vb:.10f}  "
                  f"{'완전 일치' if ok else f'★다르다 (차 {va - vb:+.3e})'}")
            if not ok:
                fails.append(f"{name}: **완전 일치여야 하는데 다르다** — "
                             f"`chunk<=0` 분기가 종전과 같은 호출이 아니다")
        else:
            r = rel(va, vb)
            ok = r < 1e-5
            print(f"  {'✅' if ok else '🚫'} {name}  상대차 {r:.3e}  (기준 1e-5)")
            if not ok:
                fails.append(f"{name}: 상대차 {r:.3e} >= 1e-5")

    print(f"\n{'=' * 96}\n  게이트")
    gate("E1 ce_c0 == sm_base", "ce_c0", "sm_base", exact=True)
    gate("E2 ce_c64 vs ce_c0", "ce_c64", "ce_c0")
    gate("E3 ce_c16 vs ce_c64", "ce_c16", "ce_c64")
    gate("E4 kd_c64 vs kd_c0", "kd_c64", "kd_c0")

    print()
    for t in tags:
        if d[t] is None:
            continue
        g = d[t].get("grad_max")
        bad = g is not None and (g != g or abs(g) == float("inf"))
        print(f"  {'🚫' if bad else '✅'} E5 {t:<10} grad_max = {g}")
        if bad:
            fails.append(f"E5 {t}: grad_max 가 유한하지 않다")

    print(f"\n{'#' * 96}\n  판정")
    for f in fails:
        print(f"  🚫 {f}")
    for s in skips:
        print(f"  ⚠️ 미평가 — {s}")
    if fails:
        print(f"\n  🚫 **{len(fails)}건 실패.** ★E1 이 실패면 분기를 먼저 고친다 — "
              f"그 아래는 전부 의미가 없다.")
    elif skips:
        print(f"\n  ⚠️ 실패 0 이지만 **미평가 {len(skips)}건**. "
              f"`run_smoke_check.bat` 을 먼저 돌리면 E1 이 평가된다.")
    else:
        print("\n  ✅ E1~E5 전부 통과. **청킹은 등가이고 기본 경로는 종전과 같다.**")
    print("#" * 96)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
