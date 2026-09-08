#!/usr/bin/env python3
"""★★**게이트 34 — 연구방향 나침반이 낡았는가.**

## 왜 있나 (2026-09-08(2차), 승인된 제안서 §3.5)

나침반(`handoff/COMPASS.md`)이 낡으면 **틀린 방향을 확신 있게 가리킨다** —
그건 없느니만 못하다. 실제로 `CLAUDE.md` 의 3차 리뷰 링크가 **대체된 v1 을
사흘 동안** 가리켰고, 그 문서가 세션 시작 프롬프트에 걸려 있어서 **판단에 바로 들어갔다.**

## 무엇을 대조하나 — ★**독립인 두 값**

| | 누가 만드나 |
|---|---|
| 나침반 행의 `마지막 실측` 번호 | ✍️**사람**이 손으로 적는다 |
| 그 축을 **제목에서** 다루는 결과문서의 최대 번호 | 🤖**실험**이 만든다 |

🚫**함정 43**(*자기 사본과 대조하는 게이트는 게이트가 아니다*)을 피하는 것이 요점이다.
두 값이 같은 손에서 나오면 **일치율 100% 는 통과가 아니라 경보**다.

## 규칙

1. `AXES` 12축이 표에 **하나씩** 있어야 한다.
2. 각 행의 `마지막 실측` 은 **`결과 NNN` 또는 `NNN`** 을 포함하거나 **`없음`** 이어야 한다.
3. ★그 축을 **헤딩에서** 다루는 결과문서 번호의 최대값이 행의 번호보다 **크면 에러**.
   (본문이 아니라 헤딩만 본다 — 본문으로 보면 매번 빨개지고,
   **아무도 안 읽는 경고는 미탐과 같다**.)
4. `다음 한 걸음`·`무엇이 뒤집나` 가 **비어 있으면 에러**(D1 — 미루려면 숫자를 적는다).

사용법
    python scripts/check_compass.py
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compass import AXES, COMPASS, result_docs, newest_mentioning   # noqa: E402

NL = chr(10)
NUM = re.compile(r"(?:결과\s*)?(\d{3})")


def main() -> int:
    print("=" * 92)
    print("  게이트 34 — 연구방향 나침반(COMPASS.md)")
    print("=" * 92)
    if not COMPASS.exists():
        print("  ⚠️ `handoff/COMPASS.md` 가 없다 — 나침반을 아직 안 만들었다. 건너뛴다.")
        return 0

    rows = {}
    for ln in io.open(COMPASS, encoding="utf-8").read().split(NL):
        if not ln.startswith("|") or ln.startswith("|---"):
            continue
        c = [x.strip() for x in ln.split("|")]
        if len(c) < 7:
            continue
        name = c[1].strip("* ")
        if name in ("축", ""):
            continue
        rows[name] = c

    docs = result_docs()
    fails, warns = [], []
    for name, keys in AXES:
        c = rows.get(name)
        if c is None:
            fails.append(f"축 `{name}` 이 표에 없다")
            continue
        last, step, flip = c[3], c[4], c[5]
        m = NUM.search(last)
        if not m and "없음" not in last:
            fails.append(f"축 `{name}` — `마지막 실측` 에 결과문서 번호도 `없음` 도 없다: {last!r}")
            continue
        cited = int(m.group(1)) if m else 0
        newest = newest_mentioning(docs, keys)
        if newest > cited:
            fails.append(f"축 `{name}` — 인용 {cited or '없음'} 인데 "
                         f"**결과 {newest} 가 제목에서 이 축을 다룬다**. 행을 갱신할 것")
        if len(step) < 4:
            fails.append(f"축 `{name}` — `다음 한 걸음` 이 비었다(D1: 선결을 숫자로)")
        if len(flip) < 4:
            fails.append(f"축 `{name}` — `무엇이 뒤집나` 가 비었다")

    extra = [n for n in rows if n not in {x for x, _ in AXES}]
    if extra:
        warns.append(f"`AXES` 에 없는 행 {len(extra)}개: {', '.join(extra)}")

    for w in warns:
        print(f"  ⚠️ {w}")
    if not fails:
        print(f"  ✅ 축 {len(AXES)}개 전부 최신 — 각 행의 인용 번호 이후로 "
              f"그 축을 제목에서 다룬 결과문서가 없다.")
        return 0
    for f in fails:
        print(f"  🚫 {f}")
    print(f"\n  🚫 {len(fails)}건 — 나침반이 낡으면 **틀린 방향을 확신 있게 가리킨다**.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
