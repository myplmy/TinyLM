#!/usr/bin/env python3
"""Validate the canonical one-plan-one-row experiment index."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / "test_plan"
INDEX = PLAN_DIR / "실험계획목록.md"
ID_RE = re.compile(r"^(P\d{3}[A-Za-z]?)_")
ROW_RE = re.compile(r"^\| \[(P\d{3}[A-Za-z]?)\]\(([^)]+)\) \|")
SECTIONS = (
    "## 1. 계획만 있고 실행 전",
    "## 2. 진행 중",
    "## 3. 종결",
)


def main() -> int:
    text = INDEX.read_text(encoding="utf-8")
    errors = []
    if "**" in text or "★" in text:
        errors.append("index contains forbidden emphasis marker ** or ★")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    if tuple(headings) != SECTIONS:
        errors.append(f"section topology differs: {headings!r}")
    if re.search(r"^#{2,}\s+\d+\.\d+", text, re.MULTILINE):
        errors.append("numbered subsection remains in the index")

    rows = []
    current = None
    row_section = {}
    for line in text.splitlines():
        if line in SECTIONS:
            current = line
        match = ROW_RE.match(line)
        if match:
            ident, filename = match.groups()
            cells = re.split(r"(?<!\\)\|", line.strip()[1:-1])
            if len(cells) != 4:
                errors.append(f"{ident} row has {len(cells)} unescaped cells, expected 4")
            rows.append((ident, filename))
            row_section[ident] = current
    counts = Counter(ident for ident, _ in rows)
    duplicates = sorted(ident for ident, count in counts.items() if count != 1)
    if duplicates:
        errors.append("duplicate plan rows: " + ", ".join(duplicates))

    docs = {}
    for path in PLAN_DIR.glob("P*.md"):
        match = ID_RE.match(path.name)
        if match:
            docs[match.group(1)] = path.name
    missing = sorted(set(docs) - set(counts))
    extra = sorted(set(counts) - set(docs))
    if missing:
        errors.append("plans missing from index: " + ", ".join(missing))
    if extra:
        errors.append("rows without physical plan document: " + ", ".join(extra))
    for ident, filename in rows:
        if docs.get(ident) != filename:
            errors.append(f"{ident} link mismatch: {filename!r} != {docs.get(ident)!r}")
        if filename.endswith("-done.md") and row_section.get(ident) != SECTIONS[2]:
            errors.append(f"{ident} -done document is outside closed table")
    for ident, filename in docs.items():
        if row_section.get(ident) == SECTIONS[2]:
            head = (PLAN_DIR / filename).read_text(encoding="utf-8")[:5000]
            if not filename.endswith("-done.md") and "종결" not in head and "닫는다" not in head:
                errors.append(f"{ident} closed row lacks explicit close evidence in plan header")

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        print(f"SUMMARY rows={len(rows)} docs={len(docs)} errors={len(errors)}")
        return 1
    print(f"[PASS] experiment plan index rows={len(rows)} docs={len(docs)} unique one-state entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
