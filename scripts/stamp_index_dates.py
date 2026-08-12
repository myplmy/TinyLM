#!/usr/bin/env python3
"""색인 표에 **최근갱신** 열을 넣고 유지한다 — `실험계획목록.md` · `실험목록.md`. GPU 0.

## 왜 (사용자 지시 2026-08-13)

> *"실험계획목록.md 과 실험목록.md 파일에 각 실험 계획/결과분석 파일별 가장 최근 갱신일자나
>  갱신버전 열 만들어서 관리했으면 함"*

이 저장소의 계획·결과 문서는 **living document** 다. 결과 038 에 §9 가, 035 에 §12.8 이
나중에 붙는 식이라 **"작성일" 은 문서의 나이를 말해주지 못한다.** 색인만 보고
*"이 계획서가 지금 사실을 반영하고 있나"* 를 판단할 수 없으면, 끝난 실험을 다시 설계하거나
낡은 계획서대로 배치를 만드는 사고가 난다(`exp-plan` 스킬이 막으려는 것이 정확히 그것).

## 어디서 날짜를 얻나 — **두 출처의 최댓값**

    max( git 의 마지막 커밋일 ,  파일 mtime )

git 만 보면 **아직 커밋 안 한 편집**이 안 보이고, mtime 만 보면 체크아웃·동기화로 흔들린다.
둘 중 **큰 쪽**이 "이 문서가 마지막으로 손댄 날" 에 가장 가깝다.
⚠️ **이건 추정이다.** 의미상의 "갱신" 이 아니라 **파일이 바뀐 날**이다.

## 멱등이다

이미 열이 있으면 **값만 갱신**하고 열을 또 만들지 않는다. 반복 실행해도 표가 안 망가진다.

사용:
    python scripts/stamp_index_dates.py            # 미리보기(파일 안 고침)
    python scripts/stamp_index_dates.py --write
"""
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COL = "최근갱신"
TARGETS = [
    (ROOT / "test_plan" / "실험계획목록.md", ROOT / "test_plan"),
    (ROOT / "test_result" / "실험목록.md", ROOT / "test_result"),
]
LINK = re.compile(r"\[[^\]]*\]\(([^)#]+\.md)")


_GIT = None


def git_dates():
    """★파일당 `git log` 를 부르면 마운트에서 분 단위로 느리다(2026-08-14 타임아웃).
    **한 번의 `git log --name-only` 로 전체 이력을 훑어** 경로별 최신 커밋일을 만든다."""
    global _GIT
    if _GIT is not None:
        return _GIT
    _GIT = {}
    try:
        out = subprocess.run(["git", "log", "--format=%ad", "--date=short", "--name-only"],
                             cwd=ROOT, capture_output=True, text=True, timeout=120)
        cur = None
        for ln in out.stdout.splitlines():
            s = ln.strip()
            if not s:
                continue
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
                cur = s
            elif cur and s not in _GIT:      # log 는 최신부터 → 처음 본 것이 최신
                _GIT[s] = cur
    except Exception as e:
        print(f"  [주의] git 이력을 못 읽었다({type(e).__name__}) — mtime 만 쓴다")
    return _GIT


def last_touched(p: Path, cache={}):
    if p in cache:
        return cache[p]
    if not p.exists():
        cache[p] = "—"
        return "—"
    mt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
    rel = p.relative_to(ROOT).as_posix()
    gd = git_dates().get(rel)
    cache[p] = max(mt, gd) if gd else mt
    return cache[p]


def process(index: Path, docdir: Path, write: bool):
    if not index.exists():
        print(f"[SKIP] {index} 없음")
        return 0
    lines = index.read_text(encoding="utf-8").splitlines()
    out, ncol, changed, stamped = [], None, 0, 0
    for ln in lines:
        s = ln.rstrip()
        if not s.startswith("|"):
            out.append(ln)
            continue
        cells = s.split("|")
        # 헤더 줄 — 열 개수를 여기서 정하고, 없으면 마지막 앞에 끼운다
        if ncol is None and COL not in s and re.search(r"\|\s*파일\s*\|", s):
            body = cells[1:-1] if cells[-1].strip() == "" else cells[1:]
            body.insert(len(body) - 1, f" {COL} ")
            ncol = len(body)
            out.append("|" + "|".join(body) + "|")
            changed += 1
            continue
        if ncol is None and COL in s:                       # 이미 열이 있다
            body = cells[1:-1] if cells[-1].strip() == "" else cells[1:]
            ncol = len(body)
            out.append(ln)
            continue
        if ncol is None:
            out.append(ln)
            continue
        body = cells[1:-1] if cells[-1].strip() == "" else cells[1:]
        # 구분선
        if all(set(c.strip()) <= set("-: ") and c.strip() for c in body):
            out.append("|" + "|".join(["---"] * ncol) + "|")
            continue
        m = LINK.search(s)
        stamp = last_touched(docdir / m.group(1)) if m else "—"
        if len(body) == ncol:                               # 이미 열이 있다 → 값만 교체
            body[-2] = f" {stamp} "
        elif len(body) == ncol - 1:                         # 열이 없다 → 끼운다
            body.insert(len(body) - 1, f" {stamp} ")
        else:
            out.append(ln)                                  # 열 수가 이상하다 → 손대지 않는다
            continue
        out.append("|" + "|".join(body) + "|")
        stamped += 1
    print(f"  {index.name:<22} 행 {stamped}개에 {COL} 기입 (헤더 변경 {changed})")
    if write:
        index.write_text("\n".join(out) + "\n", encoding="utf-8")
    return stamped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    print("=" * 70)
    print(f"  색인 {COL} 열 {'갱신' if a.write else '미리보기'}")
    print("=" * 70)
    for idx, d in TARGETS:
        process(idx, d, a.write)
    if not a.write:
        print("\n  [DRY-RUN] --write 를 붙여야 파일을 고친다.")
    else:
        print("\n  ⚠️ 이 날짜는 **파일이 바뀐 날**이지 의미상의 갱신이 아니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
