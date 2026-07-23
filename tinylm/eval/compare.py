"""dense vs tied 비교 표. 판정 대상은 손실 격차 하나."""
from __future__ import annotations

import json

from .. import paths

LOGS = paths.RUNS / "logs"


def compare(base=None, tied_tag=None):
    """dense(base) vs tied 비교. tied_tag 를 주면 그 조건 로그와 비교한다.
    태그 로그는 신규 이름 {base}_{tag} 우선, 없으면 구 이름 {tag} 로 폴백."""
    def _resolve(kind):
        if kind == "dense":
            cands = [f"{base}_dense"] if base else ["dense"]
        elif tied_tag:
            cands = [f"{base}_{tied_tag}", tied_tag] if base else [tied_tag]
        else:
            cands = [f"{base}_tied"] if base else ["tied"]
        for c in cands:
            if (LOGS / f"{c}.json").exists():
                return c
        return cands[0]

    names = {"dense": _resolve("dense"), "tied": _resolve("tied")}
    out = {}
    for a in ("dense", "tied"):
        p = LOGS / f"{names[a]}.json"
        if not p.exists():
            print(f"[compare] {p} 없음. 먼저 학습하세요."); return
        out[a] = json.loads(p.read_text())
    print(f"  (dense={names['dense']}.json  tied={names['tied']}.json)")
    d, t = out["dense"], out["tied"]
    MB = lambda n: n * 1.95 / 8 / 1024**2
    dl, tl = d["final"]["val_loss"], t["final"]["val_loss"]

    print("=" * 68)
    print("  dense 기준선 vs tied 개선판   (동일 토큰·동일 시드)")
    print("=" * 68)
    print(f"  {'':<20}{'dense':>14}{'tied':>14}{'차이':>14}")
    print("  " + "-" * 62)
    print(f"  {'파라미터':<20}{d['params']/1e6:>13.1f}M{t['params']/1e6:>13.1f}M"
          f"{d['params']/t['params']:>13.2f}x")
    print(f"  {'배포 메모리':<20}{MB(d['params']):>12.1f}MB{MB(t['params']):>12.1f}MB"
          f"{MB(d['params'])/MB(t['params']):>13.2f}x")
    print(f"  {'val loss':<20}{dl:>14.4f}{tl:>14.4f}{tl-dl:>+14.4f}")
    print(f"  {'perplexity':<20}{d['final']['ppl']:>14.2f}{t['final']['ppl']:>14.2f}"
          f"{t['final']['ppl']/d['final']['ppl']:>13.2f}x")
    print(f"  {'학습 시간(분)':<20}{d['wall_sec']/60:>14.1f}{t['wall_sec']/60:>14.1f}"
          f"{d['wall_sec']/t['wall_sec']:>13.2f}x")
    print("  " + "-" * 62)
    gap = tl - dl
    for a in ("dense", "tied"):
        if out[a].get("grad_max"):
            print(f"  {'최대 |g| ('+a+')':<20}{out[a]['grad_max']:>14.1f}"
                  f"{'  (>10이면 불안정)' if out[a]['grad_max'] > 10 else ''}")
        if out[a].get("n_skip"):
            print(f"  {'skip ('+a+')':<20}{out[a]['n_skip']:>14d}"
                  f"{'  (>0이면 LR 점검)' if out[a]['n_skip'] > 0 else ''}")

    if out["tied"].get("data") == "synthetic":
        print(f"\n  손실 격차 {gap:+.4f}")
        print("  !! 합성 데이터는 품질 판정에 쓸 수 없습니다.")
        print("     반복 구절 코퍼스는 '순수 암기' 과제라 파라미터 수가 그대로 성능이 됩니다.")
        print("     타잉은 정의상 파라미터를 줄이므로 구조적으로 불리하게 나옵니다.")
        print("     이 실행은 '파이프라인이 도는가'만 확인하는 용도입니다.")
        print("=" * 68); return
    print(f"\n  손실 격차 {gap:+.4f}   (논문 기준 MLP g=4의 예상치는 +0.05 ~ +0.07)")
    if gap <= 0.07:
        print("  -> 예상 범위 안. g를 더 키우거나 어텐션 타잉을 시험해볼 만함.")
    elif gap <= 0.15:
        print("  -> 다소 큼. prelude/coda를 3+3으로 늘리거나 g=2로 낮춰볼 것.")
    else:
        print("  -> 과도함. |g|max가 10 이상이면 학습 문제(LR)지 아키텍처 문제 아님.")
    print("=" * 68)
