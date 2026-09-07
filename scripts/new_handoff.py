#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★★핸드오프 파일 이름을 **시계가 짓는다.** AI 가 시각을 정하지 않는다.

## 왜 이 도구가 생겼나

2026-08-31 에 핸드오프 **날짜**가 순번이었던 것이 드러나 48건을 개명했고,
2026-09-06 에 **시각**도 13건이 물리적으로 불가능하다는 것이 드러나 다시 개명했다
(최대 **+18.6시간**).

★**원인은 능력이 아니라 규약의 구멍**이었다:

| # | 사실 |
|---|---|
| 1 | 세션 프롬프트에는 **`Today's date is YYYY-MM-DD`** 만 있다 — **시각이 없다** |
| 2 | 규약은 파일명에 **HHMM** 을 요구한다(`ai_dev_tool/02` §8.1) |
| 3 | 그래서 AI 는 **도구를 부르거나 지어내야** 했고, **부르라고 적힌 곳이 없었다** |

→ ★**이 도구가 3번을 없앤다.** 이름을 사람도 AI 도 안 정한다.

## 사용법

    python scripts/new_handoff.py --title "속도 바닥이 승자를 무효로 만들었다"
    python scripts/new_handoff.py --title "..." --dry-run     # 이름만 인쇄

★만든 뒤 본문을 채우고 `python scripts/check_handoff.py` 를 돌린다.
🚫**이 도구는 골격만 쓴다** — 내용은 AI 가 쓴다. 고정 8절은 `ai_dev_tool/02` §3 이 정본이다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDOFF = ROOT / "handoff"
NL = chr(10)

SKELETON = """# HANDOFF {date} {hm} — {title}

- **이전**: [`{prev}`]({prev})
- **코드가 정본**(`tinylm/`). 문서와 어긋나면 코드가 이긴다.
- **AI 는 학습/GPU 코드를 직접 실행하지 않는다** — 배치를 쓰고 사용자가 돌린다.
- **이 문서는 요약하지 않는다** — 다음 세션이 이것만 읽고 이어갈 수 있어야 한다.

---

## 0. 사용자 지시 (N건) — 원문과 처리

| # | 지시 | 처리 |
|---|---|---|

---

## 1. 가장 중요한 것 셋

---

## 2. 무엇을 했나

---

## 3. 무엇이 바뀌었나 — 코드·도구

---

## 4. ⚠️조심할 것 — 다음 세션이 밟을 자리

---

## 5. ★확보한 수치

---

## 6. ★열린 질문

---

## 7. ★다음 권장 실험 순서 — ⚙**{{합계}}h**

| 순 | id | 실험 | 배치 파일 | ⚙ | 누적 | 선결 | 근거 |
|---:|---:|---|---|---:|---:|---|---|

---

## 6b. ★사용자에게 부탁하는 것

---

## 8. 커밋 메시지

---

## 9. ★compact 프롬프트 (이번 세션이 압축될 때 남길 것)

---

## 10. ★세션 시작 프롬프트 (다음 세션이 붙여넣는 것)

---

## 11. ★참조 치트시트
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="핸드오프 파일을 **시계로** 만든다(이름을 사람이 안 정한다)")
    ap.add_argument("--title", required=True, help="첫 줄 한 줄 제목")
    ap.add_argument("--dry-run", action="store_true", help="이름만 인쇄하고 안 만든다")
    a = ap.parse_args()

    now = dt.datetime.now()
    name = f"{now:%Y%m%d%H%M}_HANDOFF.md"
    path = HANDOFF / name

    prevs = sorted(p.name for p in HANDOFF.glob("*_HANDOFF.md") if p.name != name)
    prev = prevs[-1] if prevs else "(없음)"

    print("=" * 96)
    print("  ★핸드오프 생성 — **시각은 `datetime.now()` 가 정한다**")
    print("=" * 96)
    print(f"  지금      {now:%Y-%m-%d %H:%M:%S}")
    print(f"  파일명    {name}")
    print(f"  직전 판   {prev}")

    if a.dry_run:
        print("\n  [dry-run] 만들지 않았다.")
        return 0
    if path.exists():
        # ★같은 분에 두 번 부르면 덮어쓰지 않는다(R01 계열 — 되돌릴 수 없는 것을 안 한다).
        print(f"\n  🚫이미 있다: {name} — 덮어쓰지 않는다. 1분 뒤 다시 부르거나 그 파일을 이어 쓴다")
        return 2

    body = SKELETON.format(date=f"{now:%Y-%m-%d}", hm=f"{now:%H:%M}",
                           title=a.title, prev=prev)
    data = body.encode("utf-8")
    tmp = str(path) + ".tmp"
    with io.open(tmp, "wb") as f:
        f.write(data)
    assert os.path.getsize(tmp) == len(data), "크기 불일치"
    os.replace(tmp, path)

    print(f"\n  ✅만들었다 ({len(data):,} 바이트, 골격만)")
    print("  ★다음: 본문을 채우고 `python scripts/check_handoff.py` 를 돌린다.")
    print("  ⚠️고정 8절의 정본은 `ai_dev_tool/02` §3 이다 — 이 골격은 그 사본이다.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
