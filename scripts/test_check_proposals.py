#!/usr/bin/env python3
"""Regression fixtures for the proposal format linter."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.check_proposals import validate_text


def valid_text(status="⏳판단 대기"):
    sections = []
    for number, title in enumerate((
        "배경", "목적", "성과물", "비용", "원리·근거", "방법",
        "거절하면 못 하는 것", "위험", "대안",
    ), 1):
        body = "내용"
        if number == 4:
            body = "| GPU | 0 |\n| AI 작업 | 1h |\n| 사용자가 직접 해야 하는 일 | 0 |\n| 디스크 | 1 KiB |"
        elif number == 8:
            body = "| 위험 | 완화 |\n| 계측 오판 | fixture |"
        elif number == 9:
            body = "| A | 안A |\n| B | 안B |\n| C | 안C |\n### 권장안\nB"
        sections.append(f"## {number}. {title}\n\n{body}")
    return (
        "# 제안 — fixture\n\n"
        f"> **작성** 2026-09-21 · **상태** {status} · **분류** 작업방식\n"
        "> 양식: [`proposal/README.md`](README.md) §3.\n\n---\n\n"
        + "\n\n".join(sections)
    )


def main() -> int:
    assert not validate_text(valid_text(), "20260921_fixture.md")
    empty = valid_text().replace("## 2. 목적\n\n내용", "## 2. 목적\n\n")
    assert any("section 2 is empty" in item for item in validate_text(empty, "20260921_fixture.md"))
    no_measurement = valid_text().replace("계측 오판", "일반 오판")
    assert any("measurement risk" in item for item in validate_text(no_measurement, "20260921_fixture.md"))
    bad_suffix = validate_text(valid_text(), "20260921_fixture-approved-on-going.md")
    assert any("approved-on-going" in item for item in bad_suffix)
    print("[PASS] proposal linter catches empty sections, measurement-risk and suffix-state drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
