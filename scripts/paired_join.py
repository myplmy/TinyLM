#!/usr/bin/env python3
"""★`paired_eval --dump-crops` 로 만든 크롭 손실 파일 **여러 개를 가로질러** 짝을 짓는다.

## 왜 필요한가 — 두 가지 벽 (2026-08-31)

**① 프리셋이 다르면 `paired_eval` 이 한 표에 못 넣는다.**
체크포인트가 `runs/ckpt/{preset}_{data}_{tokens}_{tag}.pt` 에 살기 때문에
`paired_eval` 은 **한 프리셋만** 로드한다. 그래서 P079 단계0(깊이 8/12/16/20)은
`paired_eval` 을 **모델 하나씩 네 번** 부를 수밖에 없었고, 네 번 다 *"쌍이 없다"* 로
**exit 2** 를 냈다. full-val 숫자는 나왔지만 **짝지은 SE 가 없다** — 즉 깊이 곡선의
어느 구간이 유의한지 말할 수 없다.

**② 재귀 이득이 "몰려 있다"는 판정에 귀무분포가 없다.**
P078 단계0 은 상위10% 비중 **30.2%**(cla1) 와 **28.6%**(cla2) 로 문턱 30% 를 사이에 두고
갈렸다. 🚫**문턱이 판정을 하고 있다.** 진짜 질문은 *"같은 크롭이 다시 이득을 보는가"* 이고,
그건 **다른 시드의 이득 벡터와의 상관**으로만 답한다. 상관이 0 이면 크롭별 이득은
재현되지 않는 잡음이고, **입력별 방문 배분(H2)은 예측기가 없어 실행 불가**다.

★**둘 다 이미 있는 자료로 답할 수 있다** — 필요한 것은 학습이 아니라 **합류**다.

## 전제

크롭은 val 셋을 `seq` 로 잘라 **순서대로** 도는 결정적 열거다. 그래서 **같은
`data`·`tokens`·`seq`** 이면 파일이 달라도 **i 번째 크롭은 같은 텍스트**다.
프리셋·아키텍처는 달라도 된다 — 그것이 이 도구의 목적이다.
🚫`micro_bs` 가 다르면 배치 경계가 달라질 수 있으므로 **경고**한다.

## 사용

    # 깊이 곡선을 짝지어 본다 (프리셋이 서로 달라도 된다)
    python scripts/paired_join.py --crops runs/logs/p079_d*.json \\
        --pairs d8_dense:d12_dense d12_dense:d16_dense d16_dense:d20_dense

    # ★재현성: 두 시드에서 같은 크롭이 이득을 보는가
    python scripts/paired_join.py --crops runs/logs/p078_cla1.json runs/logs/p078_cla1_s2.json \\
        --corr mC_cla1_ag4-mC_cla1_ag4_r20:mC_cla1_ag4_s2-mC_cla1_ag4_r20_s2

종료코드 0 = 계산됨. 2 = 자료가 안 맞아 계산 못 함.
🚫**이 도구는 판정하지 않는다** — 숫자와 자를 함께 인쇄하고 해석은 결과문서가 한다.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ★계열별 자(2σ, 실측) — 정본은 `scripts/_rulers.py` **하나뿐**이다.
#   🚫종전에는 여기에 사본이 있었고 *"값이 바뀌면 두 파일을 함께 고친다"* 는
#   주석이 붙어 있었다. 2026-08-31 재귀 자 갱신 때 **둘 다 안 고쳐졌다.**
#   주석은 게이트가 아니다(함정 18).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _rulers                                      # noqa: E402

RULERS = dict(_rulers.BAND_EN)


def family(tag: str) -> str:
    if "_r" in tag and any(c.isdigit() for c in tag.split("_r")[-1][:2]):
        return "recur"
    return "dense" if "dense" in tag else "tied"


def ruler_for(a: str, b: str) -> tuple[float, str]:
    fa, fb = family(a), family(b)
    if fa == fb:
        return RULERS[fa], f"{fa} 2σ"
    r = max(RULERS[fa], RULERS[fb])
    return r, f"계열 교차({fa}↔{fb}) — 큰 자"


def load(paths):
    """파일 여러 개 -> {tag: [loss]}, 공통 meta. 안 맞으면 (None, 사유)."""
    series, metas = {}, []
    for p in paths:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        metas.append((p, d["meta"]))
        for tag, v in d["crops"].items():
            if tag in series and series[tag] != v:
                return None, f"태그 `{tag}` 가 파일 둘에 **다른 값**으로 있다"
            series[tag] = v
    base = metas[0][1]
    for p, m in metas[1:]:
        for k in ("data", "tokens", "seq"):
            if m.get(k) != base.get(k):
                return None, (f"`{k}` 가 다르다: {base.get(k)!r} vs {m.get(k)!r} ({p}) "
                              f"— 크롭이 같은 텍스트가 아니다")
    n = {len(v) for v in series.values()}
    if len(n) != 1:
        return None, f"크롭 수가 제각각이다: {sorted(n)}"
    return (series, metas), None


def paired(x, y):
    """mean(x-y), SE, t, x 승률."""
    d = [a - b for a, b in zip(x, y)]
    n = len(d)
    m = sum(d) / n
    var = sum((v - m) ** 2 for v in d) / (n - 1)
    se = math.sqrt(var / n)
    win = sum(1 for v in d if v < 0) / n          # x 가 더 낮으면(좋으면) 승
    return m, se, (m / se if se else float("inf")), win, d


def pearson(u, v):
    n = len(u)
    mu, mv = sum(u) / n, sum(v) / n
    su = math.sqrt(sum((a - mu) ** 2 for a in u))
    sv = math.sqrt(sum((b - mv) ** 2 for b in v))
    if su == 0 or sv == 0:
        return float("nan")
    return sum((a - mu) * (b - mv) for a, b in zip(u, v)) / (su * sv)


def main() -> int:
    ap = argparse.ArgumentParser(description="크롭 손실 파일 가로지르기")
    ap.add_argument("--crops", nargs="+", required=True, help="dump-crops json (glob 가능)")
    ap.add_argument("--pairs", nargs="*", default=[], help="`A:B` — A 와 B 를 짝지어 비교")
    ap.add_argument("--corr", nargs="*", default=[],
                    help="`A-B:C-D` — (A-B) 이득벡터와 (C-D) 이득벡터의 상관")
    ap.add_argument("--all-pairs", action="store_true", help="모든 조합을 인접순으로")
    a = ap.parse_args()

    paths = []
    for pat in a.crops:
        hit = sorted(glob.glob(pat))
        paths += hit if hit else [pat]

    got, why = load(paths)
    if got is None:
        print("=" * 96)
        print(f"  🚫 합류 불가 — {why}")
        print("=" * 96)
        return 2
    series, metas = got

    print("=" * 96)
    print("  paired_join — 크롭 손실 파일을 가로질러 짝짓기 (torch 0 · GPU 0)")
    print("=" * 96)
    print(f"  파일 {len(paths)}개 · 태그 {len(series)}개 · 크롭 {len(next(iter(series.values())))}개")
    for p, m in metas:
        print(f"    · {Path(p).name:<28} preset={m.get('preset')} "
              f"seq={m.get('seq')} micro_bs={m.get('micro_bs')} "
              f"match_train_repeat={m.get('match_train_repeat')}")
    mbs = {m.get("micro_bs") for _, m in metas}
    if len(mbs) > 1:
        print(f"  ⚠️★micro_bs 가 섞여 있다 {sorted(mbs)} — 배치 경계가 달라 "
              f"크롭 정렬이 어긋났을 수 있다. **결과를 인용하기 전에 확인할 것**")

    print("\n" + "=" * 96)
    print("  결정적 full-val (파일이 달라도 같은 val 셋이면 비교 가능)")
    print("=" * 96)
    print(f"  {'태그':<24}{'full-val':>10}{'크롭 표준편차':>14}   계열")
    for tag, v in sorted(series.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        mu = sum(v) / len(v)
        sd = math.sqrt(sum((x - mu) ** 2 for x in v) / (len(v) - 1))
        print(f"  {tag:<24}{mu:>10.4f}{sd:>14.4f}   {family(tag)}")

    pairs = list(a.pairs)
    if a.all_pairs:
        ts = sorted(series, key=lambda t: sum(series[t]) / len(series[t]))
        pairs += [f"{x}:{y}" for x, y in zip(ts, ts[1:])]

    if pairs:
        print("\n" + "=" * 96)
        print("  ★paired per-crop — 같은 크롭 위에서 뺀다")
        print("=" * 96)
        print(f"  {'A vs B':<44}{'mean(A-B)':>11}{'SE':>9}{'t':>8}{'A 승률':>9}  판정")
        print("  " + "-" * 92)
        for spec in pairs:
            if ":" not in spec:
                print(f"  🚫 `{spec}` 형식이 아니다 (A:B)")
                continue
            x, y = spec.split(":", 1)
            if x not in series or y not in series:
                miss = [t for t in (x, y) if t not in series]
                print(f"  [건너뜀] 태그 없음: {', '.join(miss)}")
                continue
            m, se, t, win, _ = paired(series[x], series[y])
            rl, why_r = ruler_for(x, y)
            v = ("★유의하고 분해능 초과" if abs(t) > 2 and abs(m) > rl else
                 "유의하지만 분해능 미만" if abs(t) > 2 else
                 "구분 불가(체크포인트 수준에서도)")
            print(f"  {x + ' vs ' + y:<44}{m:>+11.4f}{se:>9.4f}{t:>8.2f}{win:>8.1%}  {v}")
            print(f"       ★쓴 자 {rl:.4f} — {why_r}")
        print("\n  ⚠️|t| ^> 2 는 **이 두 체크포인트가 다르다**만 말한다. 시드가 하나면")
        print("     아키텍처 우열의 근거가 아니다(P032 §2.2).")

    if a.corr:
        print("\n" + "=" * 96)
        print("  ★★이득이 **재현되는가** — 두 이득 벡터의 상관")
        print("=" * 96)
        print("  ⚠️이것이 H2(선택설)의 진짜 게이트다. 상위10% 비중은 **한 번의 분포 모양**이고,")
        print("     상관은 **같은 크롭이 다시 이득을 보는가**를 묻는다. 예측기가 없으면")
        print("     입력별 방문 배분은 실행할 수 없다.")
        for spec in a.corr:
            try:
                left, right = spec.split(":", 1)
                a1, b1 = left.split("-", 1)
                a2, b2 = right.split("-", 1)
            except ValueError:
                print(f"  🚫 `{spec}` 형식이 아니다 (A-B:C-D)")
                continue
            miss = [t for t in (a1, b1, a2, b2) if t not in series]
            if miss:
                print(f"  [건너뜀] 태그 없음: {', '.join(miss)}")
                continue
            g1 = [p - q for p, q in zip(series[a1], series[b1])]
            g2 = [p - q for p, q in zip(series[a2], series[b2])]
            r = pearson(g1, g2)
            n = len(g1)
            # r 의 표준오차(귀무 r=0): 1/sqrt(n-3) on Fisher z
            z = 0.5 * math.log((1 + r) / (1 - r)) if abs(r) < 1 else float("inf")
            zse = 1 / math.sqrt(n - 3)
            print(f"\n  ({a1} - {b1})  vs  ({a2} - {b2})")
            print(f"     Pearson r = {r:+.4f}   (n={n}, Fisher z {z:+.3f} = {z / zse:+.1f}σ)")
            print(f"     설명되는 분산 r^2 = {r * r:.1%}")
            if r < 0.10:
                print("     -> 🚫★**재현되지 않는다.** 크롭별 이득은 대부분 시드 잡음이다 — "
                      "**H2 는 예측기가 없어 실행 불가**")
            elif r < 0.30:
                print("     -> ⚠️**약하게 재현된다.** 상한을 계산하기 전에는 "
                      "입력별 배분의 이득을 주장하지 않는다")
            else:
                print("     -> ★**재현된다.** 크롭 수준의 예측기를 찾을 값어치가 있다 — "
                      "무엇이 그 크롭을 다르게 만드는지가 다음 질문이다")

    print("\n" + "=" * 96)
    print("  ★한계")
    print("    · 크롭 i 가 같은 텍스트라는 것은 **열거가 결정적이라는 전제**에 의존한다.")
    print("      data·tokens·seq 가 같은 것만 확인했다 — 열거 코드가 바뀌면 이 전제가 깨진다.")
    print("    · 🚫**이 도구는 아무것도 판정하지 않는다.** 숫자와 자를 인쇄할 뿐이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
