#!/usr/bin/env python3
"""PM 결과문서를 쓰기 전에 같은 계획의 문서가 이미 있는지 확인한다.

일반 `new_result.py`는 로그 파일명 앞의 세 자리 숫자와 `test_result/`를 정본으로
삼는다. Moonshot 로그는 날짜로 시작하고 계획 번호가 `PMnnn`이므로 그 도구에 넣으면
날짜 앞 세 자리를 실험 번호로 오인한다. 이 파일은 같은 중복방지 계약을
`moonshot_result/PMnnn__MOONSHOT__*__RESULT.md`에만 적용한다.

종료코드:
  0  해당 PM 계획의 결과문서가 없다 — 새로 만든다.
  3  결과문서가 있다 — 새 파일을 만들지 않고 기존 문서에 절을 추가한다.
  2  인자에서 PM 계획 번호를 찾지 못했다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "moonshot_result"
PM_ID = re.compile(r"(?<![A-Za-z0-9])(PM\d{3,})(?![A-Za-z0-9])", re.I)
RESULT_NAME = re.compile(
    r"^(PM\d{3,})__MOONSHOT__.+__RESULT\.md$", re.I)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    raw = sys.argv[1].strip()
    match = PM_ID.search(Path(raw).name) or PM_ID.search(raw)
    if not match:
        print(f"[STOP] {raw!r}에서 PM 계획 번호를 찾지 못했다.")
        return 2
    pm_id = match.group(1).upper()

    docs: list[str] = []
    logs: list[str] = []
    if RESULT_DIR.is_dir():
        for path in sorted(RESULT_DIR.iterdir()):
            if not path.is_file():
                continue
            result_match = RESULT_NAME.match(path.name)
            if result_match and result_match.group(1).upper() == pm_id:
                docs.append(path.name)
            elif f"_{pm_id}__MOONSHOT__" in path.name.upper():
                logs.append(path.name)

    print("=" * 92)
    print(f"  Moonshot 결과문서 사전 확인 — {pm_id}")
    print("=" * 92)
    print(f"  로그 {len(logs)}건")
    for name in logs:
        print(f"    - {name}")

    if docs:
        print(f"\n  [STOP] 이미 결과문서가 {len(docs)}개 있다. 새 파일을 만들지 않는다.")
        for name in docs:
            print(f"    - moonshot_result/{name}")
        print("  기존 문서에 다음 Stage 절과 실행 이력을 이어 쓴다.")
        return 3

    print(f"\n  [OK] {pm_id} 결과문서가 없다. 아래 형식으로 새로 만든다.")
    print(f"    moonshot_result/{pm_id}__MOONSHOT__주제__RESULT.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
