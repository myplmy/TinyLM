#!/usr/bin/env python3
"""★★실험 배치 **파일명 규약**을 강제한다 — 계획번호와 단계 구분자가 실재해야 한다.

## 왜 이 게이트가 생겼나 (2026-09-04 사용자 지시 8)

`run_REVIEW4_expC_bench_n5000.bat` 를 만들었다. **계획번호도 없고 단계 구분자도 없다.**
그러면 이 배치가 **어느 계획의 몇 단계인지** 를 파일명이 말하지 않고,
`test_result` 번호와도 이어지지 않는다.

> 사용자 지시: *"실험계획 번호는 **항상 이미 존재하는 실험계획 문서를 기반**으로 해야하며
>  (예: 계획서가 없는 번호로 `run_P____Stage0_pilot.bat` 같은 실험용 배치파일 작성 불가),
>  **실험계획 문서에 없는 실험계획 내 실험 구분자가 있어도 오류** 나도록 할 것
>  (예: 계획서에 Stage3 는 있지만 Stage3B 가 없는데 `run_P____Stage3B_someexp.bat` 는 작성불가)"*

## 규약

    run_P{번호}_{단계}_{요약}.bat        예) run_P084_Stage0_residency.bat
    run_P{번호}_{단계}_{요약}-done.bat   완료분

| 검사 | 무엇 |
|---|---|
| **N1** | 이름이 `run_P<숫자>_<단계>_<요약>.bat` 꼴인가 |
| **N2** | `test_plan/P<번호>_*.md` 가 **실재하는가** |
| ★**N3** | 그 계획서 본문에 **그 단계가 있는가**(`단계3` · `Stage 3` · `stage3b` 다 인정) |

🚫**도구 배치는 검사하지 않는다** — `run_queue` · `run_smoke_check` · `run_cleanup_checkpoints`
는 실험이 아니다(`scripts/batch/` 의 `tool_*` 도 마찬가지).

사용법
    python scripts/check_batch_name.py
    python scripts/check_batch_name.py --name run_P084_Stage0_residency.bat   # 만들기 전 확인
종료코드 0 = 통과 / 1 = 규약 위반
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 실험이 아닌 것 — 도구·스케줄러
EXEMPT = {"run_queue.bat", "run_smoke_check.bat", "run_cleanup_checkpoints.bat"}

RE_NAME = re.compile(r"^run_(P\d{3,})_([A-Za-z0-9]+)_([A-Za-z0-9_]+?)(-done)?\.bat$")


def plan_doc(pnum: str):
    hits = sorted((ROOT / "test_plan").glob(pnum + "_*.md"))
    return hits[0] if hits else None


def stage_present(doc: Path, stage: str) -> bool:
    """`Stage0` · `stage3b` · `단계3` 를 서로 인정한다."""
    txt = io.open(doc, encoding="utf-8", errors="replace").read()
    m = re.match(r"^(?:stage|Stage|S)?\s*(\d+)([A-Za-z]?)$", stage)
    if not m:
        return False
    n, suf = m.group(1), (m.group(2) or "")
    # 접미사가 있으면 **그 접미사까지** 계획서에 있어야 한다(3 이 있다고 3B 가 되는 게 아니다)
    pats = [rf"단계\s*{n}{suf}\b", rf"[Ss]tage\s*{n}{suf}\b", rf"단계{n}{suf}"]
    if suf:
        # 한글 계획서가 `단계3b` 를 `단계3-b` 로 쓰기도 한다
        pats += [rf"단계\s*{n}\s*-\s*{suf}\b"]
    return any(re.search(p, txt) for p in pats)


def check(name: str):
    """(errs, info) 를 돌려준다."""
    if name in EXEMPT:
        return [], [f"{name}: 도구 배치 — 검사 제외"]
    m = RE_NAME.match(name)
    if not m:
        return ([f"★**{name}** — 이름 규약 위반. "
                 f"`run_P<번호>_<단계>_<요약>.bat` 이어야 한다 "
                 f"(예: `run_P084_Stage0_residency.bat`). "
                 f"🚫계획번호와 단계가 없으면 **어느 계획의 몇 단계인지 파일명이 말하지 않는다**"], [])
    pnum, stage, slug, done = m.groups()
    doc = plan_doc(pnum)
    if doc is None:
        return ([f"★**{name}** — `test_plan/{pnum}_*.md` 가 **없다**. "
                 f"🚫**계획서 없이 배치를 만들지 않는다**(사용자 지시 2026-09-04)"], [])
    if not stage_present(doc, stage):
        return ([f"★**{name}** — 계획서 `{doc.name}` 에 **`{stage}` 단계가 없다**. "
                 f"🚫단계 3 이 있다고 **3B** 가 되는 것이 아니다 — "
                 f"계획서에 그 단계를 먼저 쓴다"], [])
    return [], [f"{name}: {pnum} · {stage} ✅ (계획서 {doc.name})"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None, help="만들기 전 이름 하나만 검사")
    ap.add_argument("--quiet", action="store_true", help="통과 항목은 인쇄하지 않는다")
    a = ap.parse_args()

    print("=" * 96)
    print("  check_batch_name — 계획번호·단계 구분자가 **실재하는가** (2026-09-04 신설)")
    print("=" * 96)

    names = ([a.name] if a.name else
             sorted(p.name for p in ROOT.glob("run_*.bat")))
    errs, info = [], []
    for n in names:
        e, i = check(n)
        errs += e
        info += i

    if not a.quiet:
        for line in info:
            print("  ✅ " + line)
    print()
    if errs:
        print(f"  🚫 파일명 규약 위반 — **{len(errs)}건**")
        for e in errs:
            print("    " + e)
        print()
        print("  ★고치는 법: ①계획서를 먼저 쓰고 ②그 계획서에 단계를 적고 ③그 번호로 개명한다.")
        print("  🚫**배치가 먼저 생기면 계획서가 사후 정당화가 된다.**")
        return 1
    print(f"  ✅ 실험 배치 {len(info)}개 — 계획번호·단계가 전부 실재한다.")
    print("  ⚠️★**이름이 옳다 ≠ 실험이 옳다.** 조건 검증은 `dryrun_batch` 와 exp-preflight 다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
