#!/usr/bin/env python3
"""핸드오프 메모 린터 — `ai_dev_tool/02_핸드오프_규약.md` §3 의 **기계 검증부**.

## 왜 이 도구가 생겼나 (2026-08-13 사용자 지적)

> *"핸드오프 메모 양식이 자주 바뀌는 것 같은데"*

**맞다. 최근 5개를 세어 보니 고정 섹션 9개 중 최대 4개가 빠진 판이 있었다.**
원인은 사람이 아니라 **구조**였다:

1. `.claude/skills/session-handoff/` 스킬이 **다른 양식**(7개 섹션, `session_*.md`,
   PR·branch·gh CLI 기반)을 강제한다. 이 저장소는 PR 을 안 쓰고 파일명도 다르다.
   → **같은 것을 두 곳에서 정의**(함정 18)했고, 그때그때 다른 쪽을 따랐다.
2. 규약이 문서에만 있고 **검사가 없었다.** 배치는 `lint_bat` 가, 진단은
   `check_diag_data` 가 보는데 **핸드오프만 아무도 안 봤다.**

→ **이 도구가 그 구멍이다.** `run_smoke_check.bat` 이 매번 돌린다.

## 무엇을 보는가

**필수 섹션 9개**(규약 §3) + **첫 줄·둘째 줄 형식** + **빈 절 금지 규칙**(규약 §7-A).

⚠️ **한계**: 섹션이 **있는지**만 본다. **내용이 옳은지는 모른다.**
통과가 "핸드오프가 충실하다" 의 증명이 아니라 **양식이 안 흔들렸다**는 뜻이다.

사용:
    python scripts/check_handoff.py              # 최신 1개
    python scripts/check_handoff.py --all        # 전부
    python scripts/check_handoff.py handoff/202608200600_HANDOFF.md
    종료코드 = 에러 개수
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDOFF = ROOT / "handoff"

# (키, 정규식, 에러인가) — 규약 §3 의 고정 섹션
REQUIRED = [
    ("지시표",   r"^##\s*0\..*(사용자 지시|지시사항)", True),
    ("최중요",   r"^##\s*1\..*(가장 중요|핵심|한 줄|세 가지)", False),
    ("부탁",     r"^##.*사용자에게 부탁하는 것", True),
    ("권장순서", r"^##.*(다음 권장 실험|권장 순서|다음 우선순위)", True),
    ("커밋",     r"^##.*커밋 메시지", True),
    ("열린질문", r"^##.*(열린 질문|아직 답이 없|미결)", True),
    ("시작프롬프트", r"^##.*(세션 시작 프롬프트|시작 프롬프트)", True),
    ("치트시트", r"^##.*(참조 치트시트|치트시트)", True),
]


SPEC_SINCE = "202608060000"      # ai_dev_tool/02 제정 이후 판만 강제한다


def lint(path: Path):
    # ★규약 제정 이전 판은 검사하지 않는다 — 지금 양식을 소급 적용하는 것은
    #   기록의 왜곡이고, 고치면 그 시점의 실제 상태를 알 수 없게 된다.
    stamp = re.match(r"(\d{12})", path.name)
    if stamp and stamp.group(1) < SPEC_SINCE:
        return [], [], [f"규약 제정({SPEC_SINCE[:8]}) 이전 판 — **검사 제외**(legacy)"]
    txt = path.read_text(encoding="utf-8")
    lines = txt.splitlines()
    err, warn, info = [], [], []

    # ── 1. 첫 줄 형식 ────────────────────────────────────────────────────────
    #   `# HANDOFF {YYYY-MM-DD HH:MM} — {한 줄}`
    #   ★2026-08-13: `# 핸드오프 202608200600 — ...` 로 쓴 판이 있었다. 규약 위반이다.
    if not lines:
        return ["빈 파일이다"], warn, info
    if not re.match(r"^#\s*HANDOFF\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s*[—-]", lines[0]):
        err.append(f"L1 첫 줄 형식 위반 — `# HANDOFF YYYY-MM-DD HH:MM — 한 줄` 이어야 한다: "
                   f"{lines[0][:60]}")

    # ── 2. 머리말 3요소 (규약 §3) ────────────────────────────────────────────
    head = "\n".join(lines[:12])
    if not re.search(r"이전\*{0,2}\s*[:：]", head):
        err.append("머리말에 **이전 핸드오프 링크**가 없다 (`이전: [...](...)`)")
    if "코드가 정본" not in head:
        warn.append("머리말에 *\"코드가 정본(`tinylm/`)\"* 상용구가 없다")
    if "직접 실행하지 않는다" not in head:
        warn.append("머리말에 *\"AI 는 학습/GPU 코드를 직접 실행하지 않는다\"* 상용구가 없다")
    if "요약하지 않는다" not in head:
        warn.append("머리말에 *\"이 문서는 요약하지 않는다\"* 가 없다")

    # ── 3. 고정 섹션 ─────────────────────────────────────────────────────────
    for key, pat, is_err in REQUIRED:
        if not re.search(pat, txt, re.M):
            (err if is_err else warn).append(
                f"★필수 섹션 **{key}** 가 없다 (규약 §3 고정 섹션)")

    # ── 4. 지시표는 표여야 한다 ──────────────────────────────────────────────
    m = re.search(r"^##\s*0\..*$", txt, re.M)
    if m:
        seg = txt[m.end(): m.end() + 2500]
        if "|" not in seg.split("\n##")[0]:
            err.append("§0 이 **표가 아니다** — 규약 §3 은 "
                       "`지시한 것 | AI 가 판단한 목적 | 필요했던 작업 | 실제로 한 것 | 결과` "
                       "5열 표를 요구한다. **목적을 따로 적는 것이 이 표의 존재 이유다**")
        elif "목적" not in seg.split("\n##")[0]:
            warn.append("§0 표에 **\"목적\" 열이 없다** — 지시와 목적을 분리하는 것이 규약의 핵심")

    # ── 5. 커밋 메시지: **제목이 본문과 구분돼야 한다** ──────────────────────
    #   ★2026-08-13 사용자 지적: *"커밋메시지 제안시 제목을 누락하지 않도록"*
    # ★2026-08-13 — `finditer` 로 **모든** 후보 절을 본다. 초판은 `search` 라
    #   본문 중간의 *"커밋 메시지 제목 규칙"* 같은 **설명 절**을 먼저 잡고
    #   "코드 블록이 없다" 를 오탐했다. **가장 잘 갖춰진 절**로 판정한다.
    cands = []
    for mm in re.finditer(r"^##.*커밋 메시지.*$", txt, re.M):
        s = txt[mm.end():].split("\n## ")[0]
        cands.append((("제목" in s) + bool(re.findall(r"```[\s\S]*?```", s)), s))
    mc = bool(cands)
    if mc:
        seg = max(cands)[1]
        if "제목" not in seg:
            err.append("커밋 절에 **\"제목\" 표기가 없다** — 제목과 본문을 "
                       "**따로 라벨링**해야 사용자가 그대로 복사할 수 있다(2026-08-13 지시)")
        blocks = re.findall(r"```[\s\S]*?```", seg)
        if not blocks:
            err.append("커밋 절에 **코드 블록이 없다** — 복사 가능한 형태로 준다")
        else:
            body = re.sub(r"^```.*$", "", blocks[-1], flags=re.M).strip()
            # ★한글(가-힣)·한자·기본 기호는 정상이다. **이모지·박스문자만** 본다.
            #   초판이 `ord(c) > 0x2FFF` 로 잡아 **한글 전부를 경고**했다 —
            #   "검사가 틀렸다" 의 교과서적 사례라 여기 남긴다.
            bad = [c for c in body
                   if (0x1F300 <= ord(c) <= 0x1FAFF)      # 이모지
                   or (0x2500 <= ord(c) <= 0x25FF)        # 박스·도형
                   or ord(c) in (0x2705, 0x274C, 0x26A0)]
            if bad:
                warn.append(f"커밋 본문에 터미널에서 깨질 수 있는 문자: {sorted(set(bad))[:6]}")

    # ── 6. 규약 §7-A/B: 빈 절도 명시 ─────────────────────────────────────────
    mb = re.search(r"^##.*사용자에게 부탁하는 것.*$", txt, re.M)
    if mb:
        seg = txt[mb.end():].split("\n## ")[0]
        if not re.search(r"-done|삭제", seg):
            err.append("\"부탁\" 절에 **`-done` 배치 삭제 판정이 없다**(규약 §7-B). "
                       "없으면 **\"삭제 가능한 `-done` 배치 없음\"** 이라고 적는다")
        if len(seg.strip()) < 40:
            err.append("\"부탁\" 절이 사실상 비어 있다 — 요청이 없으면 "
                       "**\"이번에는 요청할 것이 없다\"** 라고 명시한다(규약 §7-A)")

    # ── 7. 권장순서 절의 필수 열 ─────────────────────────────────────────────
    mr = re.search(r"^##.*(다음 권장 실험|권장 순서).*$", txt, re.M)
    if mr:
        seg = txt[mr.end():].split("\n## ")[0]
        for need, why in (("배치", "배치 파일명"), ("시간", "예상 시간"), ("근거", "권장 근거")):
            if need not in seg:
                warn.append(f"권장순서 절에 **{why}** 가 안 보인다(규약 §4)")

    # ── 8. CLAUDE.md 가 이 파일을 가리키는가 ─────────────────────────────────
    cm = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if path.name not in cm:
        info.append(f"`CLAUDE.md` 의 \"현재 상태\" 줄이 이 파일을 가리키지 않는다 "
                    f"(최신 핸드오프면 갱신할 것 — 규약 §2)")
    return err, warn, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true", help="handoff/ 전부")
    ap.add_argument("--last", type=int, default=1, help="최신 N개 (기본 1)")
    a = ap.parse_args()

    if a.files:
        targets = [Path(f) for f in a.files]
    else:
        allf = sorted(HANDOFF.glob("*_HANDOFF.md"))
        targets = allf if a.all else allf[-a.last:]

    W = 96
    print("=" * W)
    print("  핸드오프 린터 — ai_dev_tool/02 §3 고정 섹션 검사")
    print("=" * W)
    total_e = 0
    for p in targets:
        e, w, i = lint(p)
        total_e += len(e)
        mark = "[OK ]" if not e else "[FAIL]"
        print(f"\n  {mark} {p.name}   (E{len(e)} W{len(w)} I{len(i)})")
        for x in e: print(f"    [E] {x}")
        for x in w: print(f"    [W] {x}")
        for x in i: print(f"    [I] {x}")
    print(f"\n  총 에러 {total_e}건")
    print("  ⚠️ 섹션이 **있는지**만 본다. 내용이 옳은지는 사람이 본다.")
    print("=" * W)
    return total_e


if __name__ == "__main__":
    sys.exit(main())
