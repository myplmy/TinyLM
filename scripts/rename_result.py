#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""결과문서 개명 — **파일과 참조를 한 번에** 바꾼다. (2026-08-24 사용자 지시)

★왜 있나
    결과가 바뀌면 제목이 낡는다. 예: `030_..._E128은-4.2배-비싸다` 는 그 시점의 판정이었고
    무KD 재측정이 수를 바꿨다. 그런데 개명은 **네 곳을 동시에** 고쳐야 한다:

      1. `test_result/NNN_....md`            파일 자체
      2. `test_result/실험목록.md`             표의 링크
      3. `test_plan/실험계획목록.md`           계획 표의 링크
      4. 그 문서를 가리키는 **모든 문서의 상대링크**(계획서·리뷰·핸드오프·CLAUDE.md…)

    ⚠️★**손으로 하면 4번을 빠뜨린다.** `check_links.py` 가 나중에 잡지만 그때는
    이미 커밋된 뒤다. 이 도구는 넷을 한 번에 하고, **먼저 보여주고** 나서 적용한다.

★규약
    · 🚫**파일을 지우지 않는다.** `mv`(개명)만 한다 — 되돌릴 수 있다.
    · 번호(`NNN`)는 **실험군 번호**다. 개명으로 번호를 바꾸지 않는다(기본 거부).
      정말 바꿔야 하면 `--allow-renumber`.
    · 기본은 **미리보기**(dry-run). 적용은 `--apply`.
    · 적용 뒤 `check_links.py` 와 `check_result_numbers.py` 를 **스스로 돌려** 보고한다.

사용법
    python scripts/rename_result.py --old 030_20260807_P046-E192는-... \
                                    --new 030_20260824_P046-E는-볼록하다-...
    python scripts/rename_result.py --old <파일명> --new <파일명> --apply
    (`.md` 는 붙여도 되고 안 붙여도 된다)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "test_result"
SCAN = ("*.md", "*.bat", "*.py", "*.tsv", "*.txt")
# ★2026-08-24 — `ROOT.rglob` 은 **거르기 전에 걷는다.** `HF/`·`data_cache/`·`runs/` 가
#   커서 네트워크 드라이브에서 수십 초가 걸렸다(`check_plan_numbers.py` 와 같은 형태).
#   ★참조가 있을 수 있는 곳만 본다 — 없는 곳을 걷지 않는 것이 거르는 것보다 빠르다.
SCAN_DIRS = ("test_result", "test_plan", "docs", "handoff", "ai_dev_tool",
             "scripts", ".claude", "util", "article")


def _norm(name: str) -> str:
    return name[:-3] if name.endswith(".md") else name


def _targets():
    for pat in SCAN:                      # 최상위 파일(CLAUDE.md·experiments.tsv·run_*.bat)
        yield from ROOT.glob(pat)
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for pat in SCAN:
            for p in base.rglob(pat):
                if "__pycache__" in p.parts:
                    continue
                yield p


def main():
    ap = argparse.ArgumentParser(description="결과문서 개명 + 참조 일괄 갱신")
    ap.add_argument("--old", required=True, help="현재 파일명(확장자 생략 가능)")
    ap.add_argument("--new", required=True, help="새 파일명(확장자 생략 가능)")
    ap.add_argument("--apply", action="store_true", help="실제로 적용한다(기본은 미리보기)")
    ap.add_argument("--allow-renumber", action="store_true",
                    help="앞 세 자리(실험군 번호)를 바꾸는 것을 허용")
    a = ap.parse_args()

    old, new = _norm(a.old), _norm(a.new)
    src, dst = RES / f"{old}.md", RES / f"{new}.md"

    print("#" * 96)
    print("  결과문서 개명 — 파일 + 실험목록 + 실험계획목록 + 모든 상대링크")
    print("#" * 96)
    if not src.exists():
        print(f"  [STOP] 원본이 없다: {src.relative_to(ROOT)}")
        return 1
    if dst.exists():
        print(f"  [STOP] 대상이 이미 있다: {dst.relative_to(ROOT)}")
        return 1

    on, nn = re.match(r"(\d{3})", old), re.match(r"(\d{3})", new)
    if not on or not nn:
        print("  [STOP] 파일명이 세 자리 번호로 시작해야 한다(실험군 번호)")
        return 1
    if on.group(1) != nn.group(1) and not a.allow_renumber:
        print(f"  [STOP] 번호가 바뀐다 {on.group(1)} -> {nn.group(1)}.")
        print("         ★번호는 **실험군 번호**이고 로그 파일명이 그것을 말한다.")
        print("         정말 바꾸려면 --allow-renumber. 대개는 개명이 아니라 **이관**이 맞다.")
        return 1

    hits = []
    for p in _targets():
        try:
            s = p.read_text(encoding="utf-8")
        except Exception:                                            # noqa: BLE001
            continue
        n = s.count(old)
        if n:
            hits.append((p, n))

    print(f"\n  개명   {src.name}\n      -> {dst.name}")
    print(f"\n  참조를 고칠 파일 {len(hits)}개 (총 {sum(n for _p, n in hits)}곳)")
    for p, n in sorted(hits, key=lambda x: str(x[0])):
        star = " ★" if p.name in ("실험목록.md", "실험계획목록.md") else "  "
        print(f"   {star}{n:>3}곳  {p.relative_to(ROOT)}")

    names = {p.name for p, _n in hits}
    if "실험목록.md" not in names:
        print("\n  🚫★**`test_result/실험목록.md` 에 이 문서 참조가 없다.**")
        print("     결과문서는 반드시 실험목록에 행이 있어야 한다(규약). 개명 전에 확인할 것.")
    if "실험계획목록.md" not in names:
        print("\n  ⚠️`test_plan/실험계획목록.md` 에는 참조가 없다 — **대개 정상**이다.")
        print("     그 표는 계획서(P번호)를 링크하지 결과문서 파일명을 링크하지 않는다.")

    if not a.apply:
        print("\n  [미리보기] 적용하려면 --apply 를 붙이세요. 아무것도 바꾸지 않았다.")
        print("#" * 96)
        return 0

    for p, _n in hits:
        s = p.read_text(encoding="utf-8")
        p.write_text(s.replace(old, new), encoding="utf-8")
    src.rename(dst)
    print(f"\n  ✅ 개명 완료 + 참조 {len(hits)}개 파일 갱신. 🚫**지운 것은 없다**(mv).")

    print("\n  ── 자체 검증 ──")
    for chk in ("check_links.py", "check_result_numbers.py"):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / chk)],
                           capture_output=True, text=True)
        tail = [l for l in r.stdout.splitlines() if l.strip()][-3:]
        print(f"   [{'OK ' if r.returncode == 0 else 'FAIL'}] {chk}")
        for l in tail:
            print(f"        {l}")
    print("#" * 96)
    print("  ⚠️이 도구는 **문자열 치환**이다. 파일명이 다른 문장의 부분 문자열이면 함께 바뀐다.")
    print("  ⚠️★**지난 핸드오프의 링크도 함께 바뀐다.** 기록 왜곡처럼 보이지만, 안 바꾸면")
    print("     그 링크가 깨진다 — **가리키는 대상은 같고 이름만 바뀐 것**이라 갱신이 맞다.")
    print("     🚫핸드오프의 **본문 서술**은 절대 고치지 않는다(그건 그때의 판단 기록이다).")
    print("     결과문서 파일명은 충분히 길어 실무상 안전하지만, 위 목록을 눈으로 볼 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
