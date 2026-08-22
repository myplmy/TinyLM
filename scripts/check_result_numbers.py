#!/usr/bin/env python3
"""★★**결과문서 번호 규약 검사.** torch·GPU 0.

## 왜 이 검사가 생겼나 (2026-08-22 사용자 지적, 실사고)

`CLAUDE.md` 산출물 규칙:

    test_result/{실험번호}_{YYYYMMDDHHMMSS}_{요약}.md
    같은 실험군은 한 파일에 이어 쓰고, 성격이 다르면 새 번호로 분리

★**번호는 "실험군" 이지 "세션" 이 아니다.** 그리고 ★**로그 파일명이 이미 번호를 말한다** —
`003_log_…P014…`, `051_log_…P065…`, `053_log_…P067…`.

🚫**그런데 나는 그 셋을 `054` 라는 새 번호 하나에 뭉쳤다.** 원인은 단순하다:
**세 로그가 같은 배치 실행에서 나와서 내 머릿속에 "하나의 사건" 이 됐다.**
★**문서 번호는 사건이 아니라 실험군을 센다** — *"내가 언제 봤는가"* 가 아니라
*"무엇에 대한 것인가"* 로 나눈다.

## 무엇을 보나

| # | 검사 | 판정 |
|---|---|---|
| **R1** | `NNN_log_*.txt` 가 있는데 **같은 번호의 결과문서(`NNN_*.md`)가 없다** | 🚫**에러** |
| **R2** | 같은 번호의 결과문서가 **둘 이상** | ⚠️경고(분할은 규약 위반은 아니나 의도 확인) |
| **R3** | `실험목록.md` 에 없는 결과문서 번호 | ⚠️경고 |
| **R4** | 번호 없는 `.md`(`_삭제바람_` 등) | ℹ️정보 — 개명 대기로 본다 |

⚠️**이 검사는 "번호가 맞는가" 만 본다.** **내용이 옳은 실험군에 들어갔는지**는 사람이 본다.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "test_result"
NUM = re.compile(r"^(\d{3})_")


def main():
    print("=" * 96)
    print("  결과문서 번호 규약 — 로그 번호 ↔ 결과문서 번호 ↔ 실험목록")
    print("=" * 96)

    docs, logs, unnumbered = defaultdict(list), defaultdict(list), []
    for p in sorted(RES.iterdir()):
        if p.name == "실험목록.md" or not p.is_file():
            continue
        m = NUM.match(p.name)
        if not m:
            unnumbered.append(p.name)
            continue
        (logs if "_log_" in p.name else docs)[m.group(1)].append(p.name)

    idx = (RES / "실험목록.md").read_text(encoding="utf-8") if (RES / "실험목록.md").exists() else ""

    err, warn, info = [], [], []

    # R1 — 로그는 있는데 결과문서가 없다
    for n, ls in sorted(logs.items()):
        if n not in docs:
            err.append(f"R1 **{n}번 로그 {len(ls)}건이 있는데 결과문서 `{n}_*.md` 가 없다** "
                       f"— 로그 파일명이 번호를 말하고 있다: {ls[0]}")

    # R2 — 같은 번호 문서 여럿
    for n, ds in sorted(docs.items()):
        if len(ds) > 1:
            warn.append(f"R2 {n}번 결과문서가 {len(ds)}개다: {ds}")

    # R3 — 실험목록 누락
    for n in sorted(docs):
        if f"| **{n}" not in idx and f"| {n} " not in idx and f"| **{n}**" not in idx:
            warn.append(f"R3 {n}번이 실험목록.md 에 안 보인다 (표기 변형일 수 있다)")

    for u in unnumbered:
        info.append(f"R4 번호 없는 파일: {u}")

    print(f"\n  결과문서 {sum(len(v) for v in docs.values())}개 / "
          f"로그 {sum(len(v) for v in logs.values())}개 / 번호 없음 {len(unnumbered)}개")
    print(f"  번호 범위: {min(docs) if docs else '-'} ~ {max(docs) if docs else '-'}")
    # 빈 번호(결번)
    if docs:
        used = sorted(int(n) for n in docs)
        gaps = [i for i in range(used[0], used[-1] + 1) if i not in used]
        if gaps:
            info.append(f"결번: {[f'{g:03d}' for g in gaps]} — "
                        f"★**다음 신규 실험군이 쓸 수 있는 번호**다")

    for e in err:
        print(f"  🚫 {e}")
    for w in warn:
        print(f"  ⚠️ {w}")
    for i in info:
        print(f"  ℹ️  {i}")

    print(f"\n  {'✅ 통과' if not err else f'🚫 {len(err)}건 실패'}  "
          f"(경고 {len(warn)} / 정보 {len(info)})")
    print("  ⚠️★번호가 맞는지만 본다. **내용이 옳은 실험군에 들어갔는지는 사람이 본다.**")
    print("=" * 96)
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
