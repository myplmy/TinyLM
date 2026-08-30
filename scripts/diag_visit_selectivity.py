"""P078 단계0 — **재귀의 이득은 퍼져 있는가, 몰려 있는가.** torch 0 · GPU 0 · 학습 0.

## 왜 이 질문인가

방문을 늘리면 품질이 오른다(결과 059 §13: 8->28 방문 −0.0390). **그런데 왜 오르는지를
우리는 모른다.** 두 가지 설명이 있고 **배포 결정이 갈린다**:

| 가설 | 뜻 | 참이면 |
|---|---|---|
| **H1 용량설** | 방문이 늘면 **모든 입력에 조금씩** 더 잘한다 | 방문 수는 그냥 **연산 예산**이다. 균일하게 깎아도 된다 |
| ★**H2 선택설** | **어려운 입력에서만** 크게 좋아진다 | ★**입력마다 방문 수를 다르게 줄 수 있다** — 평균 지연을 크게 줄인다 |

★**평균으로는 이 둘이 구분되지 않는다.** −0.0107 이라는 한 수는
*"1,464 크롭이 전부 −0.0107"* 이든 *"146 크롭이 −0.107 이고 나머지는 0"* 이든 같다.
→ **분포를 봐야 한다.**

## 무엇을 보나 (`paired_eval --dump-crops` 의 산출물을 읽는다)

| 지표 | H1 이면 | ★**H2 이면** |
|---|---|---|
| 이득 `d_i = base_i - deep_i` 의 **지니계수** | 낮다(균일) | ★**높다(집중)** |
| 상위 10% 크롭이 차지하는 이득 비중 | 약 10% | ★**30% 이상** |
| 이득이 **양수인 크롭 비율** | 100% 에 가깝다 | 절반 근처 — **손해 보는 크롭도 있다** |
| `base_i`(난이도) 와 `d_i` 의 상관 | 0 근처 | ★**양수** — 어려운 크롭에서 더 번다 |

★★**판정 기준**(사전에 정한다 — 함정 34: 나중에 기준을 만들지 않는다)

    상위10% 비중 ^< 20%  이고  상관 ^< 0.15   -> **H1**. 방문은 균일한 연산 예산이다
    상위10% 비중 ^> 30%  또는  상관 ^> 0.30   -> ★**H2**. 입력별 방문 배분을 설계할 값어치가 있다
    그 사이                                  -> 판정 보류. 크롭 수를 늘리거나 다른 축을 본다

⚠️**크롭은 문서가 아니다.** seq 1024 로 자른 조각이라 *"어려운 크롭"* 이 *"어려운 과제"*
와 같지 않다. 🚫**이 도구로 "재귀는 추론이다" 를 결론짓지 않는다** — 그 주장은 과제 단위
평가가 필요하고, 여기서는 **H2 가 볼 만한가**만 정한다.

    python scripts/paired_eval.py --models mC_cla1_ag4 mC_cla1_ag4_r20 --match-train-repeat \\
        --dump-crops runs/logs/p078_crops.json
    python scripts/diag_visit_selectivity.py --crops runs/logs/p078_crops.json \\
        --base mC_cla1_ag4 --deep mC_cla1_ag4_r20
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys
from pathlib import Path

# ★성공 기준값 — `check_diag_data` 가 이 상수의 존재를 본다(함정 32).
H1_TOP10 = 0.20        # 이 아래면 균일
H2_TOP10 = 0.30        # 이 위면 집중
H1_CORR = 0.15
H2_CORR = 0.30


def gini(xs: list[float]) -> float:
    """음수를 0 으로 자른 뒤의 지니계수. 이득이 없는 크롭은 '기여 0' 으로 센다."""
    v = sorted(max(0.0, x) for x in xs)
    n = len(v)
    s = sum(v)
    if n == 0 or s <= 0:
        return float("nan")
    cum = 0.0
    for i, x in enumerate(v, 1):
        cum += i * x
    return (2 * cum) / (n * s) - (n + 1) / n


def pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return num / (da * db) if da and db else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description="P078 단계0 — 방문 이득의 분포")
    ap.add_argument("--crops", required=True, help="paired_eval --dump-crops 의 산출물")
    ap.add_argument("--base", required=True, help="기준(방문 적음) 태그")
    ap.add_argument("--deep", required=True, help="비교(방문 많음) 태그")
    a = ap.parse_args()

    d = json.loads(Path(a.crops).read_text(encoding="utf-8"))
    crops, meta = d["crops"], d.get("meta", {})
    for t in (a.base, a.deep):
        if t not in crops:
            print(f"[!] `{t}` 가 파일에 없다. 들어 있는 태그: {sorted(crops)}")
            return 1
    base, deep = crops[a.base], crops[a.deep]
    if len(base) != len(deep):
        print(f"[!] 크롭 수가 다르다 {len(base)} vs {len(deep)} — paired 가 아니다")
        return 1

    gain = [b - x for b, x in zip(base, deep)]      # 양수 = deep 이 더 좋다
    n = len(gain)
    mean = sum(gain) / n
    sd = statistics.stdev(gain) if n > 1 else float("nan")

    order = sorted(range(n), key=lambda i: -gain[i])
    k = max(1, n // 10)
    tot_pos = sum(x for x in gain if x > 0)
    top_share = (sum(gain[i] for i in order[:k]) / tot_pos) if tot_pos > 0 else float("nan")
    pos = sum(1 for x in gain if x > 0) / n
    corr = pearson(base, gain)
    gi = gini(gain)

    print("=" * 96)
    print("  P078 단계0 — 방문 이득이 퍼져 있는가 몰려 있는가 (torch 0 · GPU 0)")
    print(f"  기준 {a.base}  vs  깊음 {a.deep}   크롭 {n}개")
    if meta:
        print(f"  meta: {meta}")
    print("=" * 96)
    print(f"  평균 이득            {mean:+.6f}   (paired_eval 의 mean 과 같아야 한다)")
    print(f"  이득 표준편차        {sd:.6f}   = 평균의 {abs(sd/mean) if mean else float('nan'):.1f}배")
    print(f"  이득이 양수인 크롭   {pos*100:5.1f}%")
    print(f"  ★상위 10% 크롭의 이득 비중  {top_share*100:5.1f}%   (균일하면 10%)")
    print(f"  지니계수(양수분)     {gi:.4f}   (0=완전균일, 1=한 크롭 독식)")
    print(f"  ★난이도-이득 상관    {corr:+.4f}   (base 손실 vs 이득)")
    print()

    # 분위별 이득 — 표로 보면 형태가 바로 보인다
    print("  난이도 십분위별 평균 이득 (base 손실 오름차순)")
    idx = sorted(range(n), key=lambda i: base[i])
    print(f"    {'십분위':>6} {'base 평균':>10} {'이득 평균':>11} {'이득 비중':>9}")
    for q in range(10):
        seg = idx[q * n // 10:(q + 1) * n // 10]
        if not seg:
            continue
        bm = sum(base[i] for i in seg) / len(seg)
        gm = sum(gain[i] for i in seg) / len(seg)
        sh = sum(gain[i] for i in seg) / tot_pos * 100 if tot_pos > 0 else float("nan")
        print(f"    {q+1:>6} {bm:>10.4f} {gm:>+11.6f} {sh:>8.1f}%")
    print()

    print("=" * 96)
    if top_share < H1_TOP10 and abs(corr) < H1_CORR:
        v = ("★**H1 용량설**. 이득이 고르게 퍼져 있다 — 방문은 균일한 연산 예산이다. "
             "🚫입력별 방문 배분을 설계할 근거가 없다")
    elif top_share > H2_TOP10 or corr > H2_CORR:
        v = ("★★**H2 선택설**. 이득이 일부 크롭에 몰려 있다 — "
             "**입력마다 방문 수를 다르게 주면 평균 지연을 크게 줄일 수 있다.** 단계1 을 연다")
    else:
        v = ("⚠️**판정 보류.** 두 기준 사이다. 크롭 수를 늘리거나 다른 몸통에서 다시 본다 — "
             "🚫여기서 기준을 옮기지 않는다(함정 34)")
    print(f"  판정: {v}")
    print(f"  기준: 상위10% ^< {H1_TOP10:.0%} 이고 |상관| ^< {H1_CORR} -> H1 / "
          f"상위10% ^> {H2_TOP10:.0%} 또는 상관 ^> {H2_CORR} -> H2")
    print()
    print("  ⚠️한계")
    print("    · 크롭은 seq 로 자른 조각이지 **과제가 아니다**. '어려운 크롭' != '추론이 필요한 문제'.")
    print("    · 🚫**이 도구로 \"재귀는 추론이다\" 를 결론짓지 않는다** — H2 가 볼 만한가만 정한다.")
    print("    · 시드 하나다. 분포의 모양이 시드에 얼마나 의존하는지는 안 쟀다.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
