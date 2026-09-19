#!/usr/bin/env python3
"""Static handoff validator for the TinyLM Codex environment.

This validator is self-contained and reads only the selected shared handoff files.
It intentionally does not consult another agent environment or project experiment
registries. Content truth still requires human review.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
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
QUEUE_HELPER_PATH = REPO_ROOT / "scripts" / "handoff_queue.py"
DEFAULT_HOURS_TARGET = 48.0
HOURS_REASON_MARK = "시간 미달 사유"
QUEUE_SPEC = importlib.util.spec_from_file_location("tinylm_handoff_queue", QUEUE_HELPER_PATH)
if QUEUE_SPEC is None or QUEUE_SPEC.loader is None:
    raise RuntimeError(f"cannot load {QUEUE_HELPER_PATH}")
HANDOFF_QUEUE = importlib.util.module_from_spec(QUEUE_SPEC)
sys.modules[QUEUE_SPEC.name] = HANDOFF_QUEUE
QUEUE_SPEC.loader.exec_module(HANDOFF_QUEUE)


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


def markdown_cells(line: str) -> list[str]:
    raw = re.split(r"(?<!\\)\|", line.strip())
    if raw and raw[0] == "":
        raw = raw[1:]
    if raw and raw[-1] == "":
        raw = raw[:-1]
    return [cell.strip().replace(r"\|", "|") for cell in raw]


def markdown_tables(body: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = body.splitlines()
    result: list[tuple[list[str], list[list[str]]]] = []
    index = 0
    while index + 1 < len(lines):
        if not lines[index].lstrip().startswith("|") or not re.match(
            r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", lines[index + 1]
        ):
            index += 1
            continue
        header = markdown_cells(lines[index])
        rows: list[list[str]] = []
        index += 2
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            cells = markdown_cells(lines[index])
            if len(cells) == len(header):
                rows.append(cells)
            index += 1
        result.append((header, rows))
    return result


def table_rows_with_columns(body: str, columns: tuple[str, ...]) -> list[list[str]] | None:
    for header, rows in markdown_tables(body):
        if all(column in header for column in columns):
            return rows
    return None


def validate(path: Path, *, hours_target: float = DEFAULT_HOURS_TARGET) -> Validation:
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
    directive_columns = ("#", "사용자가 지시한 것", "AI 가 판단한 목적", "그래서 필요했던 작업", "실제로 한 것", "결과")
    directive_rows = table_rows_with_columns(directive_body, directive_columns)
    if directive_rows is None:
        errors.append(f"directive table must contain exact semantic columns {directive_columns}")
    else:
        count_match = re.search(r"사용자 지시\s+(\d+)건", text)
        if count_match is not None and int(count_match.group(1)) != len(directive_rows):
            errors.append(
                f"directive count says {count_match.group(1)} but table has {len(directive_rows)} rows"
            )
    if re.search(r"\bN건\b", text):
        errors.append("unresolved directive count placeholder")

    change_body = section_body(text, REQUIRED_SECTIONS["3"]) or ""
    sync_columns = ("산출물", "필요 여부", "실제 diff", "미갱신 사유")
    if table_rows_with_columns(change_body, sync_columns) is None:
        errors.append(f"canonical synchronization table missing columns {sync_columns}")

    recommendation = section_body(text, REQUIRED_SECTIONS["7"]) or ""
    queue_columns = ("순", "id", "실험", "배치 파일", "⚙", "누적", "인벤토리", "실행상태", "선결", "근거")
    queue_rows = table_rows_with_columns(recommendation, queue_columns)
    if queue_rows is None:
        errors.append(f"recommendation table missing columns {queue_columns}")
    else:
        header = next(
            header for header, rows in markdown_tables(recommendation)
            if all(column in header for column in queue_columns)
        )
        inventory_index = header.index("인벤토리")
        execution_index = header.index("실행상태")
        hours_index = header.index("⚙")
        current_hours = 0.0
        for row_number, row in enumerate(queue_rows, start=1):
            inventory = row[inventory_index].strip(" `")
            execution = row[execution_index].strip(" `")
            if inventory not in HANDOFF_QUEUE.INVENTORY_STATES:
                errors.append(f"queue row {row_number} has invalid inventory state {inventory!r}")
            if execution not in HANDOFF_QUEUE.EXECUTION_STATES:
                errors.append(f"queue row {row_number} has invalid execution state {execution!r}")
            if inventory == "PRESENT" and execution not in {"DONE", "HOLD"}:
                raw_hours = row[hours_index].strip(" `⚙h시간")
                try:
                    current_hours += float(raw_hours)
                except ValueError:
                    errors.append(
                        f"queue row {row_number} has invalid hours value {row[hours_index]!r}"
                    )
        if current_hours < hours_target and HOURS_REASON_MARK not in recommendation:
            errors.append(
                f"current queue totals {current_hours:.1f}h below {hours_target:.0f}h but "
                f"section 7 lacks '{HOURS_REASON_MARK}'"
            )
    if "<br>" in recommendation.lower():
        errors.append("recommendation section must not use <br>")

    if previous is not None:
        try:
            inheritance = HANDOFF_QUEUE.inheritance_errors(path, previous_path)
        except Exception as exc:
            errors.append(f"queue inheritance check failed: {type(exc).__name__}: {exc}")
        else:
            errors.extend(inheritance)

    request_body = section_body(text, REQUIRED_SECTIONS["6b"]) or ""
    if "삭제" not in request_body or "-done" not in request_body:
        errors.append("user request section lacks explicit -done deletion disposition")
    request_columns = ("대상", "정확한 위치", "근거", "사용자가 할 행동", "완료 신호", "AI 후속 처리")
    request_rows = table_rows_with_columns(request_body, request_columns)
    if request_rows is None:
        errors.append(f"user request table missing six action columns {request_columns}")
    else:
        for row_number, row in enumerate(request_rows, start=1):
            if any(not cell.strip() for cell in row):
                errors.append(f"user request row {row_number} has an empty action field")

    caution_body = section_body(text, REQUIRED_SECTIONS["4"]) or ""
    unresolved_columns = (
        "검사", "정확한 대상", "증거와 상태", "운영 영향", "권장 조치", "대안", "승인 주체"
    )
    unresolved_rows = table_rows_with_columns(caution_body, unresolved_columns)
    if unresolved_rows is None:
        errors.append(f"unresolved-check table missing columns {unresolved_columns}")
    else:
        unresolved_header = next(
            header for header, rows in markdown_tables(caution_body)
            if all(column in header for column in unresolved_columns)
        )
        status_index = unresolved_header.index("증거와 상태")
        required_indices = [unresolved_header.index(column) for column in unresolved_columns[1:]]
        placeholders = {"", "-", "—", "TBD", "미정"}
        for row_number, row in enumerate(unresolved_rows, start=1):
            status = row[status_index]
            if re.search(r"(?:\bFAIL\b|\bBLOCKED\b|미해결|NOT_RUN_PENDING)", status, re.IGNORECASE):
                incomplete = [
                    unresolved_header[index]
                    for index in required_indices
                    if row[index].strip() in placeholders
                ]
                if incomplete:
                    errors.append(
                        f"unresolved-check row {row_number} lacks decision fields: {', '.join(incomplete)}"
                    )
    smoke_match = re.search(
        r"`?(run_smoke_check\.(?:bat|sh))`?\s*\|\s*`?"
        r"(REQUIRED_USER_RUN|NOT_RUN_PENDING|NOT_REQUIRED\([^)]+\))`?",
        caution_body,
    )
    if smoke_match is None:
        errors.append("smoke disposition is missing or invalid")
    elif smoke_match.group(2) in {"REQUIRED_USER_RUN", "NOT_RUN_PENDING"}:
        if smoke_match.group(1) not in request_body:
            errors.append("pending/required smoke is not mirrored in the user request table")

    commit_body = section_body(text, REQUIRED_SECTIONS["8"]) or ""
    if "### 제목" not in commit_body or "### 본문" not in commit_body:
        errors.append("commit section must separate title and body")
    if len(FENCE_RE.findall(commit_body)) < 2:
        errors.append("commit section needs two copyable code blocks")

    start_body = section_body(text, REQUIRED_SECTIONS["10"]) or ""
    state_match = re.search(r"열린 WIP 상태\*?\*?\s*:\s*`?(있음|없음)`?", start_body)
    if state_match is None:
        errors.append("session-start prompt lacks explicit open-WIP state")
    elif state_match.group(1) == "없음":
        if "중단 작업" in start_body:
            errors.append("session-start prompt says '중단 작업' although open-WIP state is 없음")
        if "새 요청" not in start_body:
            errors.append("no-open-WIP branch must say that a new request starts")
    else:
        if re.search(r"WIP_\d{8}[a-z]?_작업원장\.md", start_body) is None:
            errors.append("open-WIP branch lacks the exact WIP filename")
        if "첫 미완료" not in start_body:
            errors.append("open-WIP branch lacks the first incomplete item")
    for phrase in ("첫 행동", "승인 전 금지"):
        if phrase not in start_body:
            errors.append(f"session-start prompt lacks {phrase}")

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
    parser.add_argument("--hours-target", type=float, default=DEFAULT_HOURS_TARGET)
    args = parser.parse_args()
    if args.hours_target <= 0:
        parser.error("--hours-target must be positive")

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
        result = validate(path, hours_target=args.hours_target)
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
