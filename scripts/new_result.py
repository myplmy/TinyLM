"""결과문서를 **쓰기 전에** 돌린다 — 그 번호에 이미 문서가 있는가.

★왜 생겼나 (2026-08-27)
    `031` 이 **20일 동안** 결과문서 두 개로 갈라져 있었다. 정적 게이트가 R2 를
    **경고**로만 냈고, 경고는 매 세션 통과했다. 실험목록에도 031 행이 두 줄이라
    인용할 때 어느 쪽을 가리켜야 하는지 알 수 없었다.

    스킬 `log-to-result` 는 *"같은 실험군이면 기존 번호에 이어 쓴다"* 고 **적어만** 뒀다.
    **"먼저 있는지 본다" 는 절차가 없었다.** 규약을 한 줄 더 쓰는 대신 절차를 도구로 옮긴다.

사용

    python scripts/new_result.py test_result/059_log_20260827_P074_stage1_dense_depth_curve.txt
    python scripts/new_result.py 059

종료코드
    0  그 번호에 결과문서가 **없다** — 새로 만든다. 파일명 골격을 인쇄한다.
    3  그 번호에 결과문서가 **있다** — **새로 만들지 말고 그 문서에 절을 이어 쓴다.**
    2  인자가 번호를 말하지 않는다.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "test_result"
NUM = re.compile(r"^(\d{3})_")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    arg = sys.argv[1].strip()
    m = re.search(r"(\d{3})", Path(arg).name)
    if not m:
        print(f"🚫 {arg!r} 에서 세 자리 번호를 못 찾았다. "
              f"**로그 파일명 앞 세 자리가 실험군 번호다.**")
        return 2
    n = m.group(1)

    docs, logs = [], []
    for p in sorted(RES.iterdir()):
        if not p.is_file() or p.name == "실험목록.md":
            continue
        mm = NUM.match(p.name)
        if not mm or mm.group(1) != n:
            continue
        (logs if "_log_" in p.name else docs).append(p.name)

    print("=" * 92)
    print(f"  결과문서 사전 확인 — {n} 번")
    print("=" * 92)
    print(f"  로그 {len(logs)}건")
    for f in logs:
        print(f"    - {f}")

    if docs:
        print(f"\n  ★**이미 결과문서가 {len(docs)}개 있다** — 새 파일을 만들지 않는다.")
        for f in docs:
            print(f"    -^> test_result/{f}")
        print("\n  할 일")
        print("    1. 위 문서를 열어 **새 절(§)** 로 이어 쓴다. 번호는 실험군 번호이지")
        print("       실행 횟수가 아니다 — 같은 실험군의 재실행·후속 단계는 전부 한 문서다.")
        print("    2. 문서 제목이 더 이상 내용을 대표하지 않으면 "
              "`python scripts/rename_result.py` 로 개명한다(목록·링크 동시 갱신).")
        print("    3. 실험목록.md 도 **행을 늘리지 말고** 그 번호의 행을 갱신한다.")
        print("\n  🚫 새 파일을 만들면 `check_result_numbers` R2 가 **에러**로 막는다.")
        return 3

    print(f"\n  ✅ {n} 번 결과문서가 없다 — 새로 만든다.")
    print(f"     test_result/{n}_YYYYMMDD_P0NN-한줄요약.md")
    print("     (요약은 **결론**을 적는다. 실험 이름을 반복하지 않는다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
