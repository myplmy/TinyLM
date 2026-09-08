#!/usr/bin/env python3
"""★★**게이트 35 — 저장소 텍스트 파일에 제어문자가 박혔는가.**

## 왜 있나 (2026-09-08(2차), 사용자 지시 3)

**백슬래시 사고가 누적 15회**다. 형태는 언제나 같다:

    bash heredoc / 파이썬 패치 문자열 안의  \\b  \\t  \\r
        →  실제 0x08 · 0x09 · 0x0D 바이트로 파일에 박힌다

실사고: `scripts\\batch\\tool_wandb_push.bat` 이 `scripts` + **0x08** + `atch` + **0x09** + `tool_…`
이 되어 **wandb push 가 한 번도 안 돌았다.** 문법 오류가 아니라 **문법적으로 멀쩡한 쓰레기**다.

## 기존 그물의 구멍

`lint_bat` 규칙 1b·1c 가 이것을 잡는다 — 🚫**그런데 `.bat` 만 본다.**
같은 사고가 `.py`·`.md`·`.tsv` 에 나면 **아무도 안 본다.**
★이 게이트가 그 구멍을 메운다.

## 규칙

- **에러**: `0x00`~`0x08` · `0x0B` · `0x0C` · `0x0E`~`0x1F` 중 하나라도 있으면.
  (탭 `0x09` · LF `0x0A` · CR `0x0D` 는 정상 문자라 뺀다)
- ⚠️**탭은 안 본다** — `.tsv` 의 구분자이고 `.py` 의 들여쓰기로도 합법이다.
  🚫`.bat` 의 탭은 `lint_bat` 이 이미 본다. **범위를 넓히면 면제를 함께 넣는다.**
- `.bat` 은 건너뛴다(`lint_bat` 소관 — 한 개념을 두 곳에서 검사하지 않는다).

사용법
    python scripts/check_control_chars.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = ("scripts", "tinylm", "docs", "test_plan", "test_result", "ai_dev_tool",
        "handoff", "proposal", "review_request", ".claude")
EXTS = (".py", ".md", ".tsv", ".json", ".txt", ".cfg", ".toml", ".yml", ".yaml")
SKIP_DIRS = {"__pycache__", ".git", "node_modules"}

BAD = set(range(0x00, 0x09)) | {0x0B, 0x0C} | set(range(0x0E, 0x20))
NAMES = {0x00: "NUL", 0x07: "BEL", 0x08: "BS(\\b)", 0x0B: "VT(\\v)",
         0x0C: "FF(\\f)", 0x1B: "ESC"}


def _targets():
    out = []
    for d in DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXTS:
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            out.append(p)
    for name in ("CLAUDE.md", "run100m.py", "experiments.tsv"):
        p = ROOT / name
        if p.is_file():
            out.append(p)
    return sorted(set(out))


def main() -> int:
    files = _targets()
    hits = []
    for p in files:
        try:
            raw = p.read_bytes()
        except OSError:
            continue
        for i, b in enumerate(raw):
            if b in BAD:
                line = raw[:i].count(b"\n") + 1
                nm = NAMES.get(b, f"0x{b:02X}")
                ctx = raw[max(0, i - 24):i + 24].decode("utf-8", "replace")
                ctx = ctx.replace(chr(10), "\\n")
                hits.append((p, line, nm, ctx))
                break                     # 파일당 첫 건만 — 목록이 길어지면 안 읽는다

    print("=" * 92)
    print(f"  게이트 35 — 제어문자 (검사 {len(files)}파일 · `.bat` 은 lint_bat 소관)")
    print("=" * 92)
    if not hits:
        print("  ✅ 제어문자 0건.")
        return 0
    for p, line, nm, ctx in hits:
        print(f"  🚫 {p.relative_to(ROOT)}:{line}  {nm}")
        print(f"       …{ctx}…")
    print(f"\n  🚫 {len(hits)}파일 — **백슬래시 사고**다. "
          f"파이썬 패치나 heredoc 이 `\\b`·`\\v` 를 실제 바이트로 만들었다.")
    print("     ★고치는 법: 그 파일을 `Write`/`Edit` 툴로 다시 쓴다. "
          "🚫같은 방식으로 또 패치하지 않는다.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
