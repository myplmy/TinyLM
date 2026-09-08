#!/usr/bin/env python3
"""★★WIP 작업원장의 **상태를 바꾸는 유일한 통로**. 손으로 표를 고치지 않는다.

## 왜 이 도구가 생겼나 (2026-09-04 사용자 지시 6·10)

`WIP_20260903b_작업원장-done.md` 는 **상황판 2~10번이 전부 ⏳대기**인 채로 `-done` 이 붙었다.
작업은 다 끝났고 §2.x 본문도 다 썼는데 **표만 안 고쳤다.**

★원인 둘 — **둘 다 사람 탓이 아니라 구조 탓이다**:

1. **상태를 두 곳에 적었다**(본문 §2.x + 상황판 표) → 하나가 낡는다(함정 18).
2. ★★**닫기 전에 확인하는 단계가 없었다.** `mv` 한 번이면 닫혔다.

> 사용자 지시 10: *"작업원장의 각 항목 작업전, 작업완료후 작업항목 상태 변경할때마다
>  해당 작업 항목 내용에 설명 문구를 작성하는 규약으로 변경. (…) 스크립트가 작동할 때
>  **작업 상태 변경과 함께 작업내용에 대해 claude가 작성하도록 강제**하는 방식으로라도 구현할 것."*

> 사용자 지시 6: *"-done 으로 바꿀때에는 진행 상황판의 작업지시 항목이 **모두 완료 혹은 막힘이
>  아니면 변경시 오류**나도록 (…) 스크립트를 통해서만 작업원장 닫도록 할 것."*

## 사용법

    python scripts/wip.py --list
    python scripts/wip.py --start 3 --note "지시서 §9 에 프롬프트 전문 챕터 신설 착수"
    python scripts/wip.py --done  3 --note "챕터 9 신설. 복사해 붙일 수 있게 코드펜스로 감쌌다"
    python scripts/wip.py --block 5 --note "선결: 사용자 판단 대기"
    python scripts/wip.py --close                     # ⏳·🔄 가 있으면 거부한다

★`--note` 는 **필수**다. 없으면 상태가 안 바뀐다 — 그것이 이 도구의 존재 이유다.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDOFF = ROOT / "handoff"
NL = chr(10)

WAIT, RUN, DONE, BLOCK = "⏳대기", "🔄진행", "✅**완료**", "🚫**막힘**"
OPEN_MARKS = ("⏳", "🔄")


def find_ledger():
    """열려 있는 원장(=`-done` 이 아닌 것) 하나를 찾는다."""
    cands = [p for p in sorted(HANDOFF.glob("WIP_*_작업원장.md"))
             if not p.name.endswith("-done.md")]
    if not cands:
        return None
    return cands[-1]


# ★★2026-09-06 — **이스케이프된 파이프(`\|`)는 칸 구분자가 아니다.**
#   🚫사고: 2026-09-05 에 노트의 리터럴 파이프가 행을 깨서 `note.replace("|", "\\|")` 를 넣었는데,
#   **파서는 여전히 raw `|` 를 셌다** → 이스케이프한 행이 `count("|") == 6` 에 걸려
#   **상황판에서 통째로 사라졌다**(2번 행, `--list` 가 8개를 7개로 셌다).
#   ★**렌더링을 고치고 파서를 깬 것**이다 — 한 개념(칸 구분자)을 두 곳에서 다르게 정의했다(함정 18).
#   → 이제 **`_split_cells` 하나가 규약을 소유**하고 `rows`·`cells` 가 둘 다 그것을 쓴다.
def _split_cells(ln):
    """`\|`(이스케이프)를 칸 구분자로 세지 않고 자른다."""
    out, buf, i = [], [], 0
    while i < len(ln):
        ch = ln[i]
        if ch == chr(92) and i + 1 < len(ln) and ln[i + 1] == "|":
            buf.append(chr(92)); buf.append("|"); i += 2; continue
        if ch == "|":
            out.append("".join(buf)); buf = []; i += 1; continue
        buf.append(ch); i += 1
    out.append("".join(buf))
    return out


def rows(text):
    """상황판 행만 뽑는다: `| **N** | 지시 | 상태 | 작업 내용 | 산출물 |`"""
    # ★★2026-09-07 — **상황판 절 안으로 범위를 좁힌다.**
    #   🚫사고: 원장 본문(§4)에 `| **1** | ... |` 다섯 칸짜리 표를 쓰자
    #   **`--list` 가 항목을 8개에서 13개로 셌다.** 모양만 보고 있었기 때문이다.
    #   ★상황판은 `## 1. 진행 상황판` 과 **다음 `## ` 사이**에만 있다 — 그것이 정의다.
    #   ⚠️표식을 못 찾으면(옛 원장) **종전처럼 전문을 본다** — 안 그러면 과거 원장이 통째로 빈다.
    body = text.split(NL)
    lo, hi = 0, len(body)
    for i, ln in enumerate(body):
        if ln.startswith("## ") and "진행 상황판" in ln:
            lo = i + 1
            for j in range(lo, len(body)):
                if body[j].startswith("## "):
                    hi = j
                    break
            break
    out = []
    for i, ln in enumerate(body):
        if not (lo <= i < hi):
            continue
        # ★★2026-09-08(2차) — **항목 번호에 글자 꼬리를 허용한다**(`2A`·`5B`).
        #   사용자 지시가 `(2) A./B./C.` 처럼 오면 원장도 그 번호를 그대로 써야
        #   R41("항목을 줄이거나 합치지 않는다")을 기계로 지킬 수 있다.
        #   종전 정규식은 `\d+` 뿐이라 **2A~2G·5A~5C 열 행이 상황판에서 통째로 사라졌고**
        #   `--list` 가 18개를 8개로 셌다 — 인쇄와 정본이 갈라지는 그 사고다.
        #   🚫숫자만 쓰는 기존 원장은 영향 없다(꼬리는 선택).
        m = re.match(r"^\|\s*\*\*(\d+[A-Za-z]?)\*\*\s*\|", ln)
        if m and len(_split_cells(ln)) == 7:          # 칸 5개 + 양끝 빈칸 2개
            out.append((i, m.group(1), ln))
    return out


def cells(ln):
    return _split_cells(ln)       # ['', ' **N** ', ' 지시 ', ' 상태 ', ' 작업내용 ', ' 산출물 ', '']


def set_state(path, num, status, note, artifact=None):
    text = io.open(path, encoding="utf-8").read()
    hit = [(i, ln) for i, n, ln in rows(text) if n == str(num)]
    if not hit:
        print(f"  🚫 {num}번 항목이 상황판에 없다. `--list` 로 확인할 것.", file=sys.stderr)
        return 2
    i, ln = hit[0]
    c = cells(ln)
    prev = c[3].strip()
    c[3] = f" {status} "
    # ★작업 내용은 **덮어쓰지 않고 이어붙인다** — 착수 때 쓴 것과 완료 때 쓴 것이 둘 다 남아야
    #   나중에 "무엇을 하려 했고 무엇을 했나" 를 대조할 수 있다.
    old_note = c[4].strip()
    stamp = {WAIT: "대기", RUN: "착수", DONE: "완료", BLOCK: "막힘"}[status]
    # ★★2026-09-05 — 노트에 **리터럴 파이프**가 들어가면 그 행이 표에서 깨진다.
    #   실사고: `max|s-1|` 을 적었더니 `ln.count("|") == 6` 이 안 맞아 **1번 행이
    #   상황판에서 사라졌고**, `--list` 가 13개를 12개로 셌다(함정: 인쇄와 정본이 갈라진다).
    #   🚫사람에게 "쓰지 마세요" 라고 적는 대신 **도구가 고친다**.
    note = note.replace("|", "\|")
    add = f"**[{stamp}]** {note}"
    c[4] = f" {add} " if old_note in ("—", "") else f" {old_note}<br>{add} "
    if artifact:
        c[5] = f" {artifact} "
    lines = text.split(NL)
    lines[i] = "|".join(c)

    # 작업 로그에도 한 줄
    log = f"- `{stamp}` **{num}번** — {note}"
    for k in range(len(lines) - 1, -1, -1):
        if lines[k].startswith("- `") or lines[k].startswith("## 3. 작업 로그"):
            lines.insert(k + 1, log)
            break
    io.open(path, "w", encoding="utf-8", newline="").write(NL.join(lines))
    print(f"  ✅ {num}번: {prev} -> {status}")
    print(f"     {note}")
    return 0


def show(path):
    text = io.open(path, encoding="utf-8").read()
    rs = rows(text)
    print("=" * 96)
    print(f"  {path.name}  —  항목 {len(rs)}개")
    print("=" * 96)
    n_open = 0
    for _, num, ln in rs:
        c = cells(ln)
        st = c[3].strip()
        if any(m in st for m in OPEN_MARKS):
            n_open += 1
        head = re.sub(r"\s+", " ", c[2].strip())[:52]
        note = re.sub(r"<br>", " / ", c[4].strip())
        note = re.sub(r"\s+", " ", note)[:44]
        print(f"  {num:>3}  {st:<10}  {head:<54}  {note}")
    print()
    print(f"  열린 항목 {n_open}개 · 닫힌 항목 {len(rs) - n_open}개")
    if n_open:
        print("  🚫 열린 항목이 있으면 `--close` 가 거부한다.")
    return n_open


def close(path, force_note=None):
    n_open = show(path)
    print()
    if n_open:
        print("  " + "=" * 92)
        print(f"  🚫★**닫을 수 없다 — 열린 항목 {n_open}개.**")
        print("     2026-09-03 에 정확히 이 상태로 `-done` 이 붙었다(2~10번 전부 ⏳대기).")
        print("     ★작업이 끝났으면 `--done N --note \"...\"` 로 **하나씩 닫는다.**")
        print("     ★못 하는 항목이면 `--block N --note \"사유\"` 로 **사유를 남긴다.**")
        print("  " + "=" * 92)
        return 1
    # ★원문 생략 검사 — 지시를 줄여 적으면 다음 세션이 뜻을 잃는다(R41)
    text = io.open(path, encoding="utf-8").read()
    # ★**지시 셀(2번 칸)만** 본다 — 작업 내용 칸에 `(…)` 를 쓸 수 있다.
    #   🚫행 전체로 보면 내가 쓴 서술이 지시문 생략으로 오인된다(2026-09-04 오탐).
    elided = [n for _, n, ln in rows(text)
              if any(x in cells(ln)[2] for x in ("(…)", "(...)"))]
    if elided:
        print(f"  ⚠️★**지시 원문이 줄어 있다** — {', '.join(elided)}번에 `(…)` 가 있다.")
        print("     wip-ledger 규칙·R41 위반이다. 원문으로 되돌린 뒤 다시 닫는다.")
        return 1
    new = path.with_name(path.stem + "-done.md")
    path.rename(new)
    print(f"  ✅ 닫았다 -> {new.name}")
    print("  🚫**삭제하지 않는다**(규칙 R01). 개명만 한다.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    # ★2026-09-08(2차) — `type=int` 를 뗐다. 상황판이 `2A`·`5B` 를 받는데
    #   argparse 가 먼저 거절하면 그 행은 영원히 못 바꾼다.
    ap.add_argument("--start")
    ap.add_argument("--done")
    ap.add_argument("--block")
    ap.add_argument("--wait")
    ap.add_argument("--close", action="store_true")
    ap.add_argument("--note", default=None,
                    help="★필수 — 무엇을 했는지/할 것인지. 없으면 상태를 안 바꾼다")
    ap.add_argument("--artifact", default=None, help="산출물 열에 쓸 값(선택)")
    ap.add_argument("--file", default=None)
    a = ap.parse_args()

    path = Path(a.file) if a.file else find_ledger()
    if path is None or not path.is_file():
        print("  🚫 열려 있는 작업원장이 없다(`handoff/WIP_*_작업원장.md`).", file=sys.stderr)
        return 2

    if a.close:
        return close(path)
    if a.list or not any([a.start, a.done, a.block, a.wait]):
        show(path)
        return 0

    if not a.note or not a.note.strip():
        print("  🚫★**`--note` 없이는 상태를 못 바꾼다.**", file=sys.stderr)
        print("     사용자 지시 10: *상태 변경과 함께 작업내용을 쓰도록 **강제**한다*.",
              file=sys.stderr)
        print("     ★한 줄이면 된다 — 무엇을 하려는지 / 무엇을 했는지.", file=sys.stderr)
        return 2

    num, status = ((a.start, RUN) if a.start else
                   (a.done, DONE) if a.done else
                   (a.block, BLOCK) if a.block else (a.wait, WAIT))
    return set_state(path, num, status, a.note.strip(), a.artifact)


if __name__ == "__main__":
    sys.exit(main())
