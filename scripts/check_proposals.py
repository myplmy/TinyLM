#!/usr/bin/env python3
"""Validate TinyLM proposal structure, non-empty sections, and state suffixes."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROPOSAL = ROOT / "proposal"
ADOPTION_DATE = "20260919"
SECTION_RE = re.compile(r"(?m)^##\s+([1-9])\.\s+(.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"\{[^{}\n]+\}")


def _meaningful(body: str) -> bool:
    lines = [
        line.strip() for line in body.splitlines()
        if line.strip() and line.strip() != "---" and not line.lstrip().startswith("<!--")
    ]
    return bool(lines)


def validate_text(text: str, name: str) -> list[str]:
    errors: list[str] = []
    if not text.startswith("# 제안"):
        errors.append("H1 must start with '# 제안'")
    header = "\n".join(text.splitlines()[:12])
    for field in ("작성", "상태", "분류"):
        if field not in header:
            errors.append(f"top metadata missing {field}")
    if "proposal/README.md" not in header and "README.md" not in header:
        errors.append("top metadata missing proposal README format link")

    sections = list(SECTION_RE.finditer(text))
    numbers = [int(match.group(1)) for match in sections]
    if numbers != list(range(1, 10)):
        errors.append(f"sections must occur exactly once in order 1..9; found={numbers}")
    bodies: dict[int, str] = {}
    for index, match in enumerate(sections):
        end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
        number = int(match.group(1))
        body = text[match.end():end]
        bodies[number] = body
        if not _meaningful(body):
            errors.append(f"section {number} is empty")

    cost = bodies.get(4, "")
    for label in ("GPU", "AI 작업", "사용자가 직접 해야 하는 일", "디스크"):
        if label not in cost:
            errors.append(f"section 4 cost missing {label}")
    if cost and not re.search(r"\d", cost):
        errors.append("section 4 cost has no numeric amount")

    risk = bodies.get(8, "")
    if risk and not all(token in risk for token in ("위험", "완화", "계측")):
        errors.append("section 8 must include risk table anchors and a measurement risk")

    alternatives = bodies.get(9, "")
    for option in ("A", "B", "C"):
        if alternatives and re.search(rf"(?:\|\s*\*{{0,2}}{option}\*{{0,2}}\s*\||안\s*{option})", alternatives) is None:
            errors.append(f"section 9 missing option {option}")
    if alternatives and "권장안" not in alternatives:
        errors.append("section 9 missing recommended option")

    placeholders = PLACEHOLDER_RE.findall(text)
    if placeholders:
        errors.append(f"unresolved template placeholders={placeholders[:3]}")

    status_match = re.search(r"\*\*상태\*\*\s*([^·\n]+)", header)
    status = status_match.group(1).strip() if status_match else ""
    if name.endswith("-approved-on-going.md"):
        if not any(token in status for token in ("승인", "진행")):
            errors.append("approved-on-going suffix requires approved/in-progress status")
    elif name.endswith("-approved.md"):
        if "승인" not in status and "완료" not in status:
            errors.append("approved suffix requires approved/completed status")
    elif not any(name.endswith(suffix) for suffix in ("-rejected.md", "-superseded.md", "-conditional.md")):
        if "판단 대기" not in status:
            errors.append("no state suffix requires pending-decision status")
    return errors


def proposal_files(*, include_done: bool, include_legacy: bool, explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(raw).resolve() for raw in explicit]
    files = sorted(
        path for path in PROPOSAL.glob("*.md")
        if path.name not in {"README.md", "_TEMPLATE.md"}
        and (include_legacy or path.name[:8] >= ADOPTION_DATE)
    )
    if include_done:
        files.extend(
            path for path in sorted((PROPOSAL / "done").glob("*.md"))
            if path.name != "README.md"
        )
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*")
    parser.add_argument("--include-done", action="store_true")
    parser.add_argument("--include-legacy", action="store_true")
    args = parser.parse_args()
    files = proposal_files(
        include_done=args.include_done,
        include_legacy=args.include_legacy,
        explicit=args.files,
    )
    errors: list[str] = []
    for path in files:
        try:
            relative = path.relative_to(ROOT)
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{path}: {type(exc).__name__}: {exc}")
            continue
        for error in validate_text(text, path.name):
            errors.append(f"{relative.as_posix()}: {error}")
    for error in errors:
        print(f"[FAIL] {error}")
    scope = "root+done" if args.include_done else "root"
    if not args.include_legacy:
        scope += f">={ADOPTION_DATE}"
    print(f"SUMMARY proposals={len(files)} errors={len(errors)} scope={scope}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
