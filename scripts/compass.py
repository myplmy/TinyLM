#!/usr/bin/env python3
"""★★**연구방향 나침반**(`handoff/COMPASS.md`)의 **자동 열을 채운다.**

## 왜 있나 (2026-09-08 사용자 지시 8 → 2026-09-08(2차) 지시 2B 승인)

> 사용자 제안 원문의 취지: *"compact 이후 Claude 가 연구 방향을 잃지 않도록,
>  방법론 축별로 어디까지 왔고 다음이 무엇인지 한 장에 둔다."*

승인된 것은 **Claude 개선안**이다 — 시점 5열(과거/지난턴/이번턴/중단기/장기)을
**상태 4열**로 바꾸고, **손으로 쓰는 칸을 24개**(12축 × 2열)로 줄인 것
([제안서](../proposal/done/20260908_연구방향-길잡이-파일-approved.md) §3).

★**이 도구가 채우는 것**은 `축`·`마지막 실측` 두 열이고,
★**사람이 쓰는 것**은 `다음 한 걸음`·`무엇이 뒤집나` 두 열이다.
🚫**사람 칸을 도구가 덮어쓰지 않는다** — 덮어쓰면 나침반이 자기 사본이 되고
그것을 대조하는 게이트는 게이트가 아니다(함정 43).

## 무엇이 정본인가

| 열 | 정본 |
|---|---|
| 축 12개 | ★**이 파일의 `AXES`** — 한 곳 |
| 마지막 실측 | `test_result/` 의 **결과문서 번호**(사람이 행에 적는다) |
| 다음 한 걸음 · 뒤집는 조건 | ★**사람** |

사용법
    python scripts/compass.py            # 표를 검사하고 축 누락·중복을 인쇄
    python scripts/compass.py --stub     # 없는 축의 빈 행을 만들어 붙인다(사람이 채운다)
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPASS = ROOT / "handoff" / "COMPASS.md"
RESULTS = ROOT / "test_result"
NL = chr(10)

# ★★축 = **"판정을 받는 단위"** — 🚫`docs/methods/` 파일과 1:1 이 아니다.
#   `01_architecture.md` 하나에 깊이·폭·재귀·MLP타잉·어텐션타잉·CLA 여섯이 들어 있다.
#   (이름, 결과문서 제목에서 이 축을 가리키는 말들)
#   ⚠️★**부분문자열 오탐을 실물에 대고 걸렀다**(2026-09-08(2차) 초판):
#     `폭` → *"잔차 노름이 **폭발**한다"*(057) · *"결함을 증**폭**"*(006) · *"**문자 폭**"*(068)
#     `CLA` → *"규약(**CLA**UDE.md …)"*(051)   `풀` → *"머리·꼬리 KV 를 **풀면**"*(071)
#   → 축 이름은 **그 축에서만 쓰는 말**로 적는다. 짧은 말은 오탐의 원천이다.
AXES = [
    ("깊이",          ("깊이", "depth", "d12", "d14", "d16", "d18", "층수")),
    ("폭",            ("폭 축", "모델 폭", "width", "dim 512", "dim512",
                       "w512", "w384", "좁고 깊")),
    ("재귀",          ("재귀", "recur", "train-repeat", "train_repeat", "방문")),
    ("MLP 타잉",      ("MLP 타잉", "mlp_group", "mlp-group", "타잉")),
    ("어텐션 타잉",   ("어텐션 타잉", "attn_group", "attn-group")),
    ("CLA/KV",        ("cla_group", "cla-group", "CLA 의", "CLA 가", "CLA 를",
                       "KV 캐시", "KV캐시", "KV 회계")),
    ("양자화",        ("LUT", "3:4", "sparse34", "int8", "bpw", "양자화")),
    ("토큰·코퍼스",   ("토큰 예산", "코퍼스", "데이터 풀", "풀 크기", "유니크 토큰",
                       "1200M", "반복학습", "epoch")),
    ("옵티마이저",    ("Muon", "muon", "AdamW", "옵티마이저", "스케줄")),
    ("토크나이저/어휘", ("토크나이저", "어휘", "vocab", "tokenizer")),
    ("속도",          ("tok/s", "속도", "디코드", "ms/step", "추론")),
    ("지능/벤치",     ("held-out", "heldout", "벤치", "hellaswag", "arc_easy", "SFT", "정답CE")),
]

ROW = re.compile(r"^\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*\|")


def read_rows():
    if not COMPASS.exists():
        return []
    text = io.open(COMPASS, encoding="utf-8").read()
    out = []
    for ln in text.split(NL):
        if not ln.startswith("|") or ln.startswith("|---") or "| 축 |" in ln:
            continue
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 7:
            continue
        out.append((cells[1].strip("* "), ln))
    return out


def result_docs():
    """번호 -> (경로, 제목줄들)"""
    out = {}
    for p in sorted(RESULTS.glob("[0-9][0-9][0-9]_*.md")):
        n = int(p.name[:3])
        heads = [ln for ln in io.open(p, encoding="utf-8", errors="replace").read().split(NL)
                 if ln.startswith("#")]
        out[n] = (p, heads)
    return out


def newest_mentioning(docs, keys):
    """그 축을 **제목(헤딩)에서** 언급하는 가장 큰 결과문서 번호.

    ★본문 전체가 아니라 헤딩만 본다 — 본문에는 `재귀` 가 거의 모든 문서에 스쳐 지나가고,
    그러면 게이트가 매번 빨개진다. **아무도 안 읽는 경고는 미탐과 같다.**
    """
    best = 0
    for n, (_p, heads) in docs.items():
        blob = NL.join(heads)
        if any(k in blob for k in keys):
            best = max(best, n)
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stub", action="store_true",
                    help="표에 없는 축의 빈 행을 인쇄한다(사람이 채워 붙인다)")
    a = ap.parse_args()

    rows = dict(read_rows())
    docs = result_docs()
    print("=" * 92)
    print(f"  연구방향 나침반 — 축 {len(AXES)}개 · 결과문서 {len(docs)}편")
    print("=" * 92)
    missing = [n for n, _ in AXES if n not in rows]
    extra = [n for n in rows if n not in {x for x, _ in AXES}]
    for name, keys in AXES:
        newest = newest_mentioning(docs, keys)
        mark = "  " if name in rows else "🚫"
        print(f"  {mark} {name:<14}  헤딩에서 이 축을 다루는 최신 결과문서: {newest or '-'}")
    if missing:
        print(f"\n  🚫 표에 없는 축 {len(missing)}개: {', '.join(missing)}")
    if extra:
        print(f"  ⚠️ AXES 에 없는 행 {len(extra)}개: {', '.join(extra)}")
    if a.stub:
        print("\n  ── 붙여 넣을 빈 행 " + "-" * 60)
        for name in missing:
            print(f"| **{name}** |  |  |  |  |")
    print("\n  ★사람이 쓰는 칸은 `다음 한 걸음`·`무엇이 뒤집나` 둘뿐이다.")
    print("  🚫이 도구는 그 둘을 쓰지 않는다 — 쓰면 나침반이 자기 사본이 된다(함정 43).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
