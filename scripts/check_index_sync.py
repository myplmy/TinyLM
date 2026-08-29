#!/usr/bin/env python3
"""★색인 정합 검사 — **"연쇄 갱신 완료" 라고 적었는데 안 한 것**을 기계로 잡는다. torch·GPU 0.

## 왜 이 도구가 생겼나 (2026-08-29 사용자 지적)

2026-08-28 세션 핸드오프는 *"실험목록·BASELINES·REVIEW3·실험계획목록 연쇄"* 라고 적었다.
**그런데 그 커밋의 numstat 에 `test_result/실험목록.md` 가 아예 없었다.**
행 세 개(P030 단계2C · P074 단계1b · P074 단계2)가 **처음부터 안 들어갔고**,
그 사실을 **두 세션 동안 아무도 몰랐다**(계측함정 13 — *"조치 완료 표기 ≠ 실제 변경"*).

기존 그물이 전부 통과시켰다:

  · `check_links`          링크가 **존재하는 파일**을 가리키는지만 본다
  · `check_plan_numbers`   계획 **번호**만 본다 — 결과 색인은 안 본다
  · `check_result_numbers` 결과문서 **파일명**만 본다 — 색인 행은 안 본다

→ ★**"색인이 실제 산출물을 다 담고 있는가" 를 보는 도구가 없었다.** 이 파일이 그 구멍이다.

## 무엇을 검사하나

에러(종료코드 1):

  [E1] 실험목록 행의 **번호 ↔ 링크 파일 번호** 불일치
  [E2] 같은 번호에서 **`+` 접미사 중복**(`016+` 이 두 줄)          ★`--fix` 가 고친다
  [E3] 같은 번호에서 **`+` 접미사 건너뜀**(0,1,3 처럼 구멍)        ★`--fix` 가 고친다
  [E4] `test_result/NNN_*.md` 인데 **색인 행이 0개**
  [E5] 결과문서 머리말의 **계획서 링크**가 가리키는 파일이 없다
  [E6] `test_plan/P0NN_*.md` 인데 **실험계획목록에 행이 0개**

경고(종료코드에 영향 없음 — `--verbose` 로 전개):

  [W1] 결과문서의 **로그 stage 토큰**이 그 번호의 색인 행에 없다 ⚠️**오탐이 많다**
  [W2] 결과문서 머리말에 계획서 링크가 없다 / 계획서가 자기 결과를 참조하지 않는다
  [W3] 색인 **최근갱신 열**과 실제 최종 수정일(git ∪ mtime) 차이가 크다
  [W4] 결과문서 **첫 줄 제목**과 **파일명 요약**의 어휘가 전혀 안 겹친다(개명 누락 의심)

⚠️★**한계**: 이 도구는 **"행이 있는가" 를 본다. "행 내용이 옳은가" 는 모른다.**
   계측함정 42(본문이 남의 것)를 이 도구가 잡지는 못한다.

사용:
    python scripts/check_index_sync.py
    python scripts/check_index_sync.py --verbose      # 경고 전개
    python scripts/check_index_sync.py --fix          # E2·E3 만 자동 교정
    python scripts/check_index_sync.py --stale 21     # W3 임계일수(기본 14)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "test_result"
PLAN = ROOT / "test_plan"
RES_INDEX = RES / "실험목록.md"
PLAN_INDEX = PLAN / "실험계획목록.md"

ROWNUM = re.compile(r"^\|(\s*)(\*{0,2})(\d{3})(\+*)(\*{0,2})(\s*)\|")
PLANROW = re.compile(r"^\|\s*\*{0,2}(P\d{3})")
LINK = re.compile(r"\[[^\]]*\]\(([^)#]+\.md)")
STAGE = re.compile(r"stage[-_]?([0-9]+[A-Za-z]*)", re.I)
PLANLINK = re.compile(r"\(\.\./test_plan/([^)#]+\.md)\)")

_GIT = None


def git_dates() -> dict[str, str]:
    """★파일당 `git log` 는 마운트에서 분 단위로 느리다 — 한 번의 `--name-only` 로 훑는다."""
    global _GIT
    if _GIT is not None:
        return _GIT
    _GIT = {}
    try:
        out = subprocess.run(["git", "log", "--format=%ad", "--date=short", "--name-only"],
                             cwd=ROOT, capture_output=True, text=True, timeout=180)
        cur = None
        for ln in out.stdout.splitlines():
            s = ln.strip()
            if not s:
                continue
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
                cur = s
            elif cur and s not in _GIT:
                _GIT[s] = cur
    except Exception as e:                                     # noqa: BLE001
        print(f"  [주의] git 이력을 못 읽었다({type(e).__name__}) — mtime 만 쓴다")
    return _GIT


def last_touched(p: Path) -> str:
    if not p.exists():
        return "—"
    mt = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
    gd = git_dates().get(p.relative_to(ROOT).as_posix())
    return max(mt, gd) if gd else mt


def days_between(a: str, b: str) -> int | None:
    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except ValueError:
        return None


def result_docs() -> dict[str, Path]:
    out = {}
    for p in sorted(RES.glob("*.md")):
        if p.name == RES_INDEX.name:
            continue
        m = re.match(r"^(\d{3})_", p.name)
        if m:
            out[m.group(1)] = p
    return out


def fix_suffixes() -> int:
    """★E2·E3 자동 교정 — 같은 번호의 행을 **파일에 나타난 순서대로** 0,1,2… 로 다시 매긴다.

    링크·본문은 건드리지 않는다. 라벨 셀만 바꾼다."""
    lines = RES_INDEX.read_text(encoding="utf-8").splitlines()
    counter: dict[str, int] = defaultdict(int)
    out, changed = [], 0
    for ln in lines:
        m = ROWNUM.match(ln)
        if not m:
            out.append(ln)
            continue
        sp1, b1, num, plus, b2, sp2 = m.groups()
        want = counter[num]
        counter[num] += 1
        if len(plus) == want:
            out.append(ln)
            continue
        label = f"|{sp1}{b1}{num}{'+' * want}{b2}{sp2}|"
        out.append(label + ln[m.end():])
        changed += 1
    if changed:
        blob = ("\n".join(out) + "\n").encode("utf-8")
        assert len(blob) > 0
        RES_INDEX.write_bytes(blob)
    return changed


def check_result_index(err: list, warn: dict, stale_days: int) -> None:
    if not RES_INDEX.exists():
        err.append(f"{RES_INDEX.name} 이 없다")
        return
    docs = result_docs()
    lines = RES_INDEX.read_text(encoding="utf-8").splitlines()
    seen: dict[str, list[int]] = defaultdict(list)
    stamp_col: dict[str, str] = {}
    idx_by_num: dict[str, str] = defaultdict(str)

    for i, ln in enumerate(lines, 1):
        m = ROWNUM.match(ln)
        if not m:
            continue
        num, plus = m.group(3), m.group(4)
        seen[num].append(len(plus))
        idx_by_num[num] += "\n" + ln

        for l in LINK.findall(ln):
            base = Path(l).name
            lm = re.match(r"^(\d{3})_", base)
            if lm and lm.group(1) != num:
                err.append(f"[E1] 실험목록 L{i}: 행 번호 {num} vs 링크 파일 {lm.group(1)} ({base[:44]})")
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", ln)
        if dates:
            stamp_col[num] = max(dates, default="") if num not in stamp_col \
                else max(stamp_col[num], max(dates))

    for num, plusses in sorted(seen.items()):
        dup = sorted({n for n in plusses if plusses.count(n) > 1})
        if dup:
            err.append(f"[E2] 실험목록 {num}: `+` 개수 {dup} 중복 (총 {len(plusses)}행) "
                       f"— `--fix` 로 교정 가능")
        elif set(plusses) != set(range(len(plusses))):
            err.append(f"[E3] 실험목록 {num}: `+` 개수가 연속이 아니다 — {sorted(set(plusses))} "
                       f"— `--fix` 로 교정 가능")

    for num, p in docs.items():
        if num not in seen:
            err.append(f"[E4] `{p.name}` 에 대응하는 실험목록 행이 **0개**다")

    for lg in sorted(RES.glob("*_log_*.txt")):
        num = lg.name[:3]
        sm = STAGE.search(lg.name)
        if not sm or num not in idx_by_num:
            continue
        st = sm.group(1)
        body = idx_by_num[num].lower()
        if not any(q.lower() in body for q in (f"stage{st}", f"단계{st}", f"단계 {st}")):
            warn["W1"].append(f"{lg.name}  (`단계{st}` 언급 없음)")

    for num, p in sorted(docs.items()):
        if num in stamp_col:
            real = last_touched(p)
            d = days_between(stamp_col[num], real)
            if d is not None and d > stale_days:
                warn["W3"].append(f"{p.name[:56]}  색인 {stamp_col[num]} vs 실제 {real} ({d}일)")
        # ★첫 줄이 아니라 **첫 H1** 을 본다 — 정정 배너가 머리에 붙은 문서가 있다(008·012).
        head = next((ln for ln in p.read_text(encoding="utf-8").splitlines()[:14]
                     if ln.startswith("# ")), "")
        toks = {t for t in re.split(r"[-_\s]+", p.stem.split("_", 2)[-1]) if len(t) >= 2}
        if toks and not any(t in head for t in toks):
            warn["W4"].append(f"{p.name[:56]}  (H1 제목과 어휘가 전혀 안 겹친다: {head[:44]})")


def check_plan_index(err: list, warn: dict) -> None:
    if not PLAN_INDEX.exists():
        err.append(f"{PLAN_INDEX.name} 이 없다")
        return
    idx = PLAN_INDEX.read_text(encoding="utf-8")
    listed = set(re.findall(r"P\d{3}", idx))
    for p in sorted(PLAN.glob("P*.md")):
        m = re.match(r"^(P\d{3})", p.name)
        if m and m.group(1) not in listed:
            err.append(f"[E6] `{p.name}` 이 실험계획목록에 없다")

    for num, rp in sorted(result_docs().items()):
        head = "\n".join(rp.read_text(encoding="utf-8").splitlines()[:14])
        links = PLANLINK.findall(head)
        if not links:
            warn["W2"].append(f"{rp.name[:56]}  (머리말에 계획서 링크 없음)")
            continue
        for l in links:
            tp = PLAN / l
            if not tp.exists():
                err.append(f"[E5] {rp.name[:44]}: 계획서 링크가 실재하지 않는다 -> {l}")
                continue
            if num not in tp.read_text(encoding="utf-8"):
                warn["W2"].append(f"{tp.name[:56]}  (자기 결과문서 {num} 미참조)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="경고를 전부 펼친다")
    ap.add_argument("--fix", action="store_true", help="E2·E3(`+` 접미사)만 자동 교정")
    ap.add_argument("--stale", type=int, default=14, help="[W3] 임계 일수(기본 14)")
    a = ap.parse_args()

    if not a.quiet:
        print("=" * 96)
        print("  색인 정합 — 실험목록 · 실험계획목록 ↔ 실제 산출물")
        print("=" * 96)
        print("  ★이 도구는 **'행이 있는가'** 를 본다. **'행 내용이 옳은가' 는 모른다**(함정 42).")

    if a.fix:
        n = fix_suffixes()
        print(f"  ★`+` 접미사 재부여: {n}행 변경")

    err: list[str] = []
    warn: dict[str, list[str]] = defaultdict(list)
    check_result_index(err, warn, a.stale)
    check_plan_index(err, warn)

    print()
    for e in err:
        print(f"  \U0001f6ab {e}")

    LABEL = {
        "W1": "로그 stage 가 색인 행에 안 보인다 ⚠️**오탐 많음**(색인이 결론만 적기도 한다)",
        "W2": "결과 ↔ 계획 상호참조 누락",
        "W3": "색인 최근갱신 열이 낡았다 — `python scripts/stamp_index_dates.py --write`",
        "W4": "파일명 ↔ 첫 줄 제목 어휘 불일치(개명 누락 의심)",
    }
    if not a.quiet:
        for k in ("W1", "W2", "W3", "W4"):
            if not warn[k]:
                continue
            print(f"  ⚠️ [{k}] {LABEL[k]} — **{len(warn[k])}건**")
            items = warn[k] if a.verbose else warn[k][:3]
            for it in items:
                print(f"        · {it}")
            if not a.verbose and len(warn[k]) > 3:
                print(f"        … 외 {len(warn[k]) - 3}건 (`--verbose`)")

    if not a.quiet:
        total_w = sum(len(v) for v in warn.values())
        print()
        print(f"  에러 {len(err)}건 · 경고 {total_w}건")
        if not err:
            print("  ✅ 색인이 산출물을 전부 담고 있다(**행 수준**).")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
