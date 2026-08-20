#!/usr/bin/env python3
"""★계획번호 무결성 검사 — **번호만 배정하고 계획서를 안 만드는 사고**를 막는다. GPU 0.

## 왜 이 도구가 생겼나 (2026-08-21 사용자 지적, 의사결정함정 D16)

한 세션에서 **P064~P069 여섯 개 번호가 문서에 등장했는데 계획서는 0개**였다:

    P064  한국어 벤치마크    -> 배치까지 만들고 계획서 없음
    P065  2-tap conv        -> 08_paper_review 에 "P065 후보" 라고만
    P066  wandb             -> 스크립트 docstring 에만
    P067~9 Qwen/Gemma       -> 분석문서 §13 에 표로 배정만

그리고 **P065·P066 을 건너뛴 채 P070·P071 을 썼다.** 번호가 비면
*"그 사이에 뭔가 있었는데 사라졌나"* 를 다음 세션이 되묻는다.

## 무엇을 검사하나

  1. ★**참조 무결성** — 문서·배치·스크립트에 나온 `P0NN` 중 `test_plan/` 에 파일이 없는 것
     (`P012B` 처럼 **단계 접미사**가 붙은 것은 본 번호 `P012` 가 있으면 통과)
  2. ★**번호 연속성** — 최대 번호까지의 구멍. 구멍이 있으면 **왜 비었는지** 물어야 한다
  3. ★**배치 ↔ 계획 일치** — `run_P0NN_*.bat` 이 있는데 `test_plan/P0NN_*.md` 가 없는 것
     (**이것이 이번 사고의 정확한 형태다** — 배치가 계획서보다 먼저 생겼다)
  4. **목록 등재** — `test_plan/실험계획목록.md` 에 그 번호 행이 있는지

⚠️ **이름만 본다.** 계획서 내용이 옳은지, 배치가 그 계획을 구현하는지는 보증하지 않는다.

사용법
    python scripts/check_plan_numbers.py
    python scripts/check_plan_numbers.py --quiet     # 에러만
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "test_plan"
INDEX = PLAN / "실험계획목록.md"
SKIP_DIRS = {".git", "HF", "runs", "data_cache", "__pycache__", "article", "datasets"}
# ★이 도구 자신과 스킬 예시는 스캔하지 않는다 — docstring 이 사고 사례를 인용하므로
#   자기 자신을 "미작성 참조" 로 신고한다.
SKIP_FILES = {"scripts/check_plan_numbers.py"}
# ★`\b` 를 쓰면 안 된다 — `run_P064_stage0` 의 `_` 는 단어문자라 경계가 안 잡힌다.
#   (2026-08-21: 이 도구의 첫 판이 정확히 그 이유로 계획서를 못 찾았다. 함정 4 계열)
NUM = re.compile(r"(?<![A-Za-z0-9])P(\d{3})([A-Z]?)(?![0-9])")

# ★계획서 없이 써도 되는 번호 — **이유를 함께 적는다.** 빈 사면장을 만들지 않는다.
EXEMPT = {
    "P000": "양식 예시(`P0NN` 자리표시자)에서 쓰인다",
    "P099": "`runlog.py` 이름 게이트 회귀 테스트용 더미 번호(핸드오프 202608180600 §)",
    "P068": "2026-08-21 배정 철회 — P067 단계2 에 흡수. 철회 사실 기록에서만 언급된다",
    "P069": "2026-08-21 배정 철회 — P066 §3 단계2 가 다룬다. 철회 사실 기록에서만 언급된다",
    "P070": "2026-08-21 P065 로 개명. 의사결정함정 D16 의 사고 서술에서만 언급된다",
    "P071": "2026-08-21 P066 으로 개명. 동",
}


def banner(s, ch="="):
    print("\n" + ch * 92)
    print(f"  {s}")
    print(ch * 92)


def plan_files():
    """{번호: 파일명} — `-done` 접미사도 같은 번호로 본다."""
    out = {}
    for p in sorted(PLAN.glob("P*.md")):
        m = NUM.match(p.name)
        if m:
            out.setdefault(f"P{m.group(1)}", []).append(p.name)
    return out


def scan_refs():
    """{번호: [(파일, 원문토큰)]} — 저장소 전체에서 P0NN 참조를 긁는다."""
    refs = {}
    for pat in ("*.md", "*.bat", "*.py", "*.tsv"):
        for p in ROOT.rglob(pat):
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            if any(d in p.parts for d in SKIP_DIRS) or rel in SKIP_FILES:
                continue
            if rel.startswith(".claude/skills/"):      # 스킬 문서의 예시 번호
                continue
            try:
                s = p.read_text(encoding="utf-8")
            except Exception:                                   # noqa: BLE001
                continue
            for m in NUM.finditer(s):
                refs.setdefault(f"P{m.group(1)}", set()).add(rel)
    return refs


def main():
    ap = argparse.ArgumentParser(description="계획번호 무결성 검사")
    ap.add_argument("--quiet", action="store_true",
                    help="(예약) 현재는 출력이 이미 짧아 동작 차이가 없다")
    ap.parse_args()

    have = plan_files()
    refs = scan_refs()
    errs, warns = [], []

    banner("계획번호 무결성 검사 — 번호만 배정하고 파일을 안 만드는 사고를 막는다", "#")
    print(f"  계획서 {len(have)}개  ·  참조된 번호 {len(refs)}개")

    # 1. 참조 무결성
    missing = {n: sorted(v) for n, v in refs.items() if n not in have and n not in EXEMPT}
    if missing:
        print(f"\n  🚫 참조되는데 계획서가 없는 번호 {len(missing)}개:")
        for n, where in sorted(missing.items()):
            print(f"    {n}  <- {', '.join(where[:4])}{' …' if len(where) > 4 else ''}")
            errs.append(n)
        print("    → **번호를 붙였으면 계획서를 만든다.** 만들 생각이 없으면 **번호를 쓰지 않는다**")
        print("      (`후보`·`아이디어` 로만 적는다). 의사결정함정 D16.")

    # 2. 번호 연속성
    nums = sorted(int(n[1:]) for n in have)
    if nums:
        lo, hi = min(nums), max(nums)
        holes = [f"P{i:03d}" for i in range(lo, hi + 1)
                 if f"P{i:03d}" not in have and f"P{i:03d}" not in EXEMPT]
        if holes:
            print(f"\n  ⚠️ 번호 구멍 {len(holes)}개 (P{lo:03d}~P{hi:03d} 사이): {' '.join(holes)}")
            print("    → 비어 있으면 다음 세션이 **'사라진 실험이 있나'** 를 되묻는다.")
            warns.extend(holes)

    # 3. ★배치 ↔ 계획 (이번 사고의 정확한 형태)
    orphan = []
    for p in sorted(ROOT.glob("run_P*.bat")):
        m = re.match(r"run_(P\d{3})", p.name)
        if m and m.group(1) not in have:
            orphan.append((p.name, m.group(1)))
    if orphan:
        print(f"\n  🚫★ 배치는 있는데 계획서가 없는 것 {len(orphan)}개:")
        for name, n in orphan:
            print(f"    {name}  ->  test_plan/{n}_*.md 없음")
            errs.append(n)
        print("    → ★**배치가 계획서보다 먼저 생기면 안 된다**(`ai_dev_tool/03` §1).")

    # 4. 목록 등재
    if INDEX.exists():
        idx = INDEX.read_text(encoding="utf-8")
        unlisted = [n for n in have if n not in idx]
        if unlisted:
            print(f"\n  ⚠️ 실험계획목록.md 에 없는 계획서 {len(unlisted)}개: {' '.join(sorted(unlisted))}")
            warns.extend(unlisted)

    print(f"\n{'=' * 92}")
    print(f"  총 에러 {len(set(errs))}건 / 경고 {len(set(warns))}건")
    print("  ⚠️ 이 검사는 **번호와 파일의 존재**만 본다. 계획 내용이 옳은지는 사람이 본다.")
    print("=" * 92)
    return len(set(errs))


if __name__ == "__main__":
    sys.exit(main())
