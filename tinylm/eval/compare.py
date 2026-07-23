"""비교 표. 기본은 dense vs tied(태그), --vs 주면 tied vs tied."""
from __future__ import annotations

import json

from .. import paths

LOGS = paths.RUNS / "logs"


def _resolve(base, kind, tagname=None):
    if kind == "dense":
        cands = [f"{base}_dense"] if base else ["dense"]
    elif tagname:
        cands = [f"{base}_{tagname}", tagname] if base else [tagname]
    else:
        cands = [f"{base}_tied"] if base else ["tied"]
    for c in cands:
        if (LOGS / f"{c}.json").exists():
            return c
    return cands[0]


def compare(base=None, tied_tag=None, vs_tag=None):
    if vs_tag:                                  # tied vs tied
        llabel = tied_tag or "tied"; lname = _resolve(base, "tied", tied_tag)
        rlabel = vs_tag;             rname = _resolve(base, "tied", vs_tag)
        verdict = False
    else:                                       # dense vs tied
        llabel = "dense"; lname = _resolve(base, "dense")
        rlabel = f"tied:{tied_tag}" if tied_tag else "tied"
        rname = _resolve(base, "tied", tied_tag)
        verdict = True

    out = {}
    for role, nm in (("L", lname), ("R", rname)):
        p = LOGS / f"{nm}.json"
        if not p.exists():
            print(f"[compare] {p} 없음. 먼저 학습하세요."); return
        out[role] = json.loads(p.read_text())
    d, t = out["L"], out["R"]
    MB = lambda n: n * 1.95 / 8 / 1024**2
    dl, tl = d["final"]["val_loss"], t["final"]["val_loss"]

    print(f"  (좌={lname}.json  우={rname}.json)")
    print("=" * 68)
    print(f"  {llabel} 기준 vs {rlabel}   (동일 토큰·동일 시드)")
    print("=" * 68)
    print(f"  {'':<18}{llabel:>16}{rlabel:>16}{'차이(우-좌)':>14}")
    print("  " + "-" * 62)
    print(f"  {'파라미터':<18}{d['params']/1e6:>15.1f}M{t['params']/1e6:>15.1f}M"
          f"{d['params']/t['params']:>13.2f}x")
    print(f"  {'배포 메모리':<18}{MB(d['params']):>14.1f}MB{MB(t['params']):>14.1f}MB"
          f"{MB(d['params'])/MB(t['params']):>13.2f}x")
    print(f"  {'val loss':<18}{dl:>16.4f}{tl:>16.4f}{tl-dl:>+14.4f}")
    print(f"  {'perplexity':<18}{d['final']['ppl']:>16.2f}{t['final']['ppl']:>16.2f}"
          f"{t['final']['ppl']/d['final']['ppl']:>13.2f}x")
    print(f"  {'학습 시간(분)':<18}{d['wall_sec']/60:>16.1f}{t['wall_sec']/60:>16.1f}"
          f"{d['wall_sec']/t['wall_sec']:>13.2f}x")
    print("  " + "-" * 62)
    gap = tl - dl
    for role, lab in (("L", llabel), ("R", rlabel)):
        if out[role].get("grad_max"):
            print(f"  {'최대 |g| ('+lab+')':<20}{out[role]['grad_max']:>14.1f}"
                  f"{'  (>10이면 불안정)' if out[role]['grad_max'] > 10 else ''}")

    if out["R"].get("data") == "synthetic":
        print(f"\n  손실 격차 {gap:+.4f}")
        print("  !! 합성 데이터는 품질 판정에 쓸 수 없습니다(파이프라인 전용).")
        print("=" * 68); return

    if verdict:
        print(f"\n  손실 격차 {gap:+.4f}   (논문 기준 MLP g=4의 예상치는 +0.05 ~ +0.07)")
        if gap <= 0.07:
            print("  -> 예상 범위 안. g를 더 키우거나 어텐션 타잉을 시험해볼 만함.")
        elif gap <= 0.15:
            print("  -> 다소 큼. prelude/coda를 3+3으로 늘리거나 g=2로 낮춰볼 것.")
        else:
            print("  -> 과도함. |g|max가 10 이상이면 학습 문제(LR)지 아키텍처 문제 아님.")
    else:
        print(f"\n  손실 차이(우-좌) {gap:+.4f}   ({rlabel}가 {llabel}보다 "
              f"{'낮음(좋음)' if gap < 0 else '높음'})")
    print("=" * 68)
