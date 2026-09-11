#!/usr/bin/env python3
"""Static handoff validator for the TinyLM Codex environment.

This validator is self-contained and reads only the selected shared handoff files.
It intentionally does not consult another agent environment or project experiment
registries. Content truth still requires human review.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
HANDOFF_ROOT = REPO_ROOT / "handoff"

REQUIRED_SECTIONS = {
    "0": re.compile(r"^##\s*0\..*(?:사용자 지시|지시사항)", re.MULTILINE),
    "1": re.compile(r"^##\s*1\..*(?:가장 중요|핵심|세 가지)", re.MULTILINE),
    "2": re.compile(r"^##\s*2\.", re.MULTILINE),
    "3": re.compile(r"^##\s*3\.", re.MULTILINE),
    "4": re.compile(r"^##\s*4\.", re.MULTILINE),
    "5": re.compile(r"^##\s*5\.", re.MULTILINE),
    "6": re.compile(r"^##\s*6\..*(?:열린 질문|미결)", re.MULTILINE),
    "7": re.compile(r"^##\s*7\..*(?:다음 권장 실험|권장 순서)", re.MULTILINE),
    "6b": re.compile(r"^##\s*6b\..*사용자에게 부탁하는 것", re.MULTILINE),
    "8": re.compile(r"^##\s*8\..*커밋 메시지", re.MULTILINE),
    "9": re.compile(r"^##\s*9\..*compact", re.MULTILINE),
    "10": re.compile(r"^##\s*10\..*세션 시작 프롬프트", re.MULTILINE),
    "11": re.compile(r"^##\s*11\..*참조 치트시트", re.MULTILINE),
}

LOCAL_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FENCE_RE = re.compile(chr(96) * 3 + r"[\s\S]*?" + chr(96) * 3)


@dataclass
class Validation:
    path: Path
    errors: list[str]
    warnings: list[str]


def section_body(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    if match is None:
        return None
    following = text[match.end() :]
    next_heading = re.search(r"^##\s", following, re.MULTILINE)
    return following[: next_heading.start() if next_heading else None]


def is_nonempty(body: str | None) -> bool:
    if body is None:
        return False
    meaningful = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and line.strip() != "---"
    ]
    return bool(meaningful)


def validate(path: Path) -> Validation:
    errors: list[str] = []
    warnings: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    filename_match = re.fullmatch(r"(\d{8})(\d{4})_HANDOFF\.md", path.name)
    if filename_match is None:
        errors.append("filename must be YYYYMMDDHHMM_HANDOFF.md")
    if not lines:
        return Validation(path, ["file is empty"], warnings)

    title_match = re.match(
        r"^#\s*HANDOFF\s+(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})\s*[—-]\s*\S",
        lines[0],
    )
    if title_match is None:
        errors.append("first line must be HANDOFF YYYY-MM-DD HH:MM with a title")
    elif filename_match is not None:
        body_stamp = "".join(title_match.groups())
        if body_stamp != "".join(filename_match.groups()):
            errors.append("filename timestamp and first-line timestamp differ")

    head = "\n".join(lines[:12])
    previous = re.search(r"\*\*이전\*\*\s*:\s*\[[^\]]+\]\(([^)]+)\)", head)
    if previous is None:
        errors.append("header has no previous handoff link")
    else:
        previous_path = (path.parent / previous.group(1)).resolve()
        try:
            previous_path.relative_to(HANDOFF_ROOT.resolve())
        except ValueError:
            errors.append("previous handoff link leaves the handoff directory")
        else:
            if not previous_path.is_file():
                errors.append("previous handoff target does not exist")

    for label, pattern in REQUIRED_SECTIONS.items():
        body = section_body(text, pattern)
        if body is None:
            errors.append(f"missing required section {label}")
        elif not is_nonempty(body):
            errors.append(f"required section {label} is empty")

    directive_body = section_body(text, REQUIRED_SECTIONS["0"]) or ""
    for column in ("지시", "목적", "필요했던 작업", "실제로 한 것", "결과"):
        if column not in directive_body:
            errors.append(f"directive table missing column {column}")
    if re.search(r"\bN건\b", text):
        errors.append("unresolved directive count placeholder")

    recommendation = section_body(text, REQUIRED_SECTIONS["7"]) or ""
    for column in ("순", "id", "실험", "배치", "⚙", "누적", "선결", "근거"):
        if column not in recommendation:
            errors.append(f"recommendation table missing column {column}")

    request_body = section_body(text, REQUIRED_SECTIONS["6b"]) or ""
    if "삭제" not in request_body or "-done" not in request_body:
        errors.append("user request section lacks explicit -done deletion disposition")

    commit_body = section_body(text, REQUIRED_SECTIONS["8"]) or ""
    if "### 제목" not in commit_body or "### 본문" not in commit_body:
        errors.append("commit section must separate title and body")
    if len(FENCE_RE.findall(commit_body)) < 2:
        errors.append("commit section needs two copyable code blocks")

    for target in LOCAL_LINK_RE.findall(text):
        lowered = target.lower()
        if target.startswith("#") or lowered.startswith(("http://", "https://", "mailto:")):
            continue
        target_path = target.split("#", 1)[0].split("?", 1)[0]
        if not target_path:
            continue
        resolved = (path.parent / target_path).resolve()
        try:
            resolved.relative_to(REPO_ROOT)
        except ValueError:
            errors.append(f"local link leaves repository: {target}")
            continue
        if not resolved.exists():
            errors.append(f"broken local link: {target}")

    if "STATIC_ONLY" not in text or "E2E_NOT_RUN" not in text:
        warnings.append("current Codex evidence-state pair is not explicit")
    if "NOT_RUN" not in text:
        warnings.append("no explicit NOT_RUN boundary")

    return Validation(path, errors, warnings)


def resolve_targets(arguments: list[str]) -> list[Path]:
    if arguments:
        targets = [(REPO_ROOT / argument).resolve() for argument in arguments]
    else:
        targets = sorted(HANDOFF_ROOT.glob("*_HANDOFF.md"))[-1:]
    for path in targets:
        path.relative_to(HANDOFF_ROOT.resolve())
    return targets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    try:
        targets = resolve_targets(args.files)
    except (ValueError, IndexError) as exc:
        print(f"FAIL target: {exc}")
        return 2
    if not targets:
        print("FAIL target: no handoff file")
        return 2

    error_count = 0
    for path in targets:
        result = validate(path)
        print(f"CHECK {path.relative_to(REPO_ROOT).as_posix()}")
        for error in result.errors:
            print(f"  FAIL {error}")
        for warning in result.warnings:
            print(f"  WARN {warning}")
        if not result.errors:
            print("  PASS static structure and local links")
        error_count += len(result.errors)
    print(f"SUMMARY files={len(targets)} errors={error_count}")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
