#!/usr/bin/env python3
"""WIP v2 ledger writer: one audited API for state, schema and compact capsules.

The six-column contract is:
``# | 사용자 지시 | 상태 | 작업 내용 | 산출물 | 이어받을 지점``.
Legacy ledgers are read-only unless an explicit, approval-recorded migration is
requested.  All writes use compare-before plus same-directory atomic replace.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
HANDOFF = ROOT / "handoff"
NL = "\n"

WAIT, RUN, DONE, BLOCK = "⏳대기", "🔄진행", "✅**완료**", "🚫**막힘**"
OPEN_MARKS = ("⏳", "🔄")
V2_HEADER = ("#", "사용자 지시", "상태", "작업 내용", "산출물", "이어받을 지점")
LEGACY_HEADERS = {
    ("#", "지시", "상태", "작업 내용", "산출물"),
    ("#", "사용자 지시", "상태", "작업 내용", "산출물"),
    ("#", "지시", "상태", "산출물", "이어받을 지점"),
    ("#", "사용자 지시", "상태", "산출물", "이어받을 지점"),
}
BOARD_HEADING = "## 1. 진행 상황판"
LOG_HEADING = "## 3. 작업 로그 (append-only)"
AUDIT_HEADING = "## 4. 오버라이드 수정 이력 (append-only)"
CAPSULE_HEADING = "## 5. Compact 상태 캡슐 (v1)"
CAPSULE_FIELDS = (
    "현재 지시·허용목록",
    "보호·NOT_RUN 경계",
    "열린 WIP·미완료 상태",
    "수행 변경·검증",
    "막힘·승인·미확인",
    "사용자 소유 실행",
    "폐기·정정 주장",
    "다음 행동·선결",
)


@dataclass(frozen=True)
class Table:
    heading_index: int
    header_index: int
    end_index: int
    header: tuple[str, ...]
    rows: tuple[tuple[int, str, list[str]], ...]

    @property
    def is_v2(self) -> bool:
        return self.header == V2_HEADER


def _configure_utf8_streams() -> None:
    """Prevent a successful write from being followed by a CP949 print crash."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _split_cells(line: str) -> list[str]:
    """Split Markdown cells without treating an escaped pipe as a delimiter."""
    out: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(line):
        char = line[i]
        if char == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            buf.extend(("\\", "|"))
            i += 2
            continue
        if char == "|":
            out.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(char)
        i += 1
    out.append("".join(buf))
    return out


def _markdown_cells(line: str) -> list[str]:
    cells = _split_cells(line)
    if len(cells) >= 2 and not cells[0].strip() and not cells[-1].strip():
        cells = cells[1:-1]
    return [cell.strip() for cell in cells]


def _escape_cell(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    return value.replace("|", r"\|") or "—"


def _render_row(cells: Iterable[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def find_ledgers() -> list[Path]:
    return [
        path
        for path in sorted(HANDOFF.glob("WIP_*_작업원장.md"))
        if not path.name.endswith("-done.md")
    ]


def resolve_ledger(file_arg: str | None, *, allow_multiple_for_list: bool = False) -> Path:
    if file_arg:
        candidate = Path(file_arg)
        path = (ROOT / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        try:
            path.relative_to(HANDOFF.resolve())
        except ValueError as exc:
            raise ValueError("WIP path must stay inside handoff/") from exc
        if not path.is_file():
            raise ValueError(f"ledger does not exist: {path}")
        return path
    ledgers = find_ledgers()
    if not ledgers:
        raise ValueError("열려 있는 작업원장이 없다")
    if len(ledgers) > 1 and not allow_multiple_for_list:
        names = ", ".join(path.name for path in ledgers)
        raise ValueError(f"열린 작업원장이 {len(ledgers)}개다; --file 필수: {names}")
    return ledgers[-1]


def parse_table(text: str) -> Table:
    lines = text.splitlines()
    heading_hits = [i for i, line in enumerate(lines) if line.strip() == BOARD_HEADING]
    if len(heading_hits) != 1:
        raise ValueError(f"'{BOARD_HEADING}' heading count must be 1")
    heading = heading_hits[0]
    end = next((i for i in range(heading + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    header_index = next(
        (i for i in range(heading + 1, end) if lines[i].lstrip().startswith("| # |")),
        -1,
    )
    if header_index < 0 or header_index + 1 >= end:
        raise ValueError("progress table header/separator is missing")
    header = tuple(_markdown_cells(lines[header_index]))
    if header != V2_HEADER and header not in LEGACY_HEADERS:
        raise ValueError(f"unsupported WIP header: {header}")
    expected = len(header)
    parsed: list[tuple[int, str, list[str]]] = []
    for index in range(header_index + 2, end):
        match = re.match(r"^\|\s*\*\*(\d+[A-Za-z]?)\*\*\s*\|", lines[index])
        if not match:
            continue
        cells = _markdown_cells(lines[index])
        if len(cells) != expected:
            raise ValueError(f"item {match.group(1)} has {len(cells)} cells, expected {expected}")
        parsed.append((index, match.group(1), cells))
    if not parsed:
        raise ValueError("progress table has no item rows")
    ids = [item_id for _, item_id, _ in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate item id in progress table")
    return Table(heading, header_index, end, header, tuple(parsed))


def _require_v2(table: Table) -> None:
    if not table.is_v2:
        raise ValueError("LEGACY_READ_ONLY: --list만 허용; 승인 기록을 둔 --migrate-v2 필요")


def _metadata(text: str, label: str, default: str = "미기록") -> str:
    match = re.search(rf"(?m)^- \*\*{re.escape(label)}\*\*: (.+)$", text)
    return match.group(1).strip() if match else default


def _board_sha(lines: list[str], table: Table) -> str:
    board = NL.join(lines[table.header_index : table.end_index]).rstrip() + NL
    return _sha_text(board)


def _section_bounds(lines: list[str], heading: str) -> tuple[int, int] | None:
    hits = [i for i, line in enumerate(lines) if line.strip() == heading]
    if not hits:
        return None
    if len(hits) != 1:
        raise ValueError(f"heading count must be 1: {heading}")
    start = hits[0]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return start, end


def _append_to_section(lines: list[str], heading: str, body_lines: list[str]) -> None:
    bounds = _section_bounds(lines, heading)
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend((heading, "", *body_lines))
        return
    _, end = bounds
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    lines[end:end] = ([""] if end and lines[end - 1].strip() else []) + body_lines + [""]


def _capsule_values(path: Path, text: str, table: Table) -> dict[str, str]:
    rows = [(item_id, cells) for _, item_id, cells in table.rows]
    open_rows = [
        (item_id, cells[2], cells[5])
        for item_id, cells in rows
        if any(mark in cells[2] for mark in OPEN_MARKS)
    ]
    done_rows = [(item_id, cells[4]) for item_id, cells in rows if DONE in cells[2]]
    blocked = [(item_id, cells[3], cells[5]) for item_id, cells in rows if BLOCK in cells[2]]
    first = next((row for row in open_rows if RUN in row[1]), open_rows[0] if open_rows else None)
    open_text = ", ".join(f"{item_id}:{status}" for item_id, status, _ in open_rows) or "없음"
    done_text = ", ".join(f"{item_id}:{artifact}" for item_id, artifact in done_rows) or "완료 항목 없음"
    blocked_text = "; ".join(f"{item_id} {note} / {resume}" for item_id, note, resume in blocked)
    if not blocked_text:
        blocked_text = "명시적 막힘 없음; 승인·미확인은 각 행의 작업 내용·이어받을 지점이 정본"
    next_text = "모든 항목 닫힘" if first is None else f"{first[0]}번: {first[2]} (현재 {first[1]})"
    return {
        "현재 지시·허용목록": (
            f"사용자 지시 {len(rows)}건 원문={path.relative_to(ROOT).as_posix()} 상황판; "
            f"변경 허용목록={_metadata(text, '변경 허용 범위')}"
        ),
        "보호·NOT_RUN 경계": _metadata(text, "NOT_RUN 경계"),
        "열린 WIP·미완료 상태": f"{path.relative_to(ROOT).as_posix()}; 미완료={open_text}",
        "수행 변경·검증": done_text,
        "막힘·승인·미확인": blocked_text,
        "사용자 소유 실행": _metadata(text, "사용자 소유 실행", "없음으로 기록됨"),
        "폐기·정정 주장": _metadata(text, "폐기·정정 주장", "없음으로 기록됨"),
        "다음 행동·선결": next_text,
    }


def refresh_capsule(path: Path, lines: list[str]) -> list[str]:
    text = NL.join(lines)
    table = parse_table(text)
    _require_v2(table)
    values = _capsule_values(path, text, table)
    block = [
        CAPSULE_HEADING,
        "",
        f"- **상황판 SHA-256**: `{_board_sha(lines, table)}`",
        f"- **갱신시각**: `{_now()}`",
        "- **증거 수준**: `STATIC_ONLY`; manual/auto compact E2E는 별도 판정",
        "",
        "| 필드 | 값 |",
        "|---|---|",
    ]
    block.extend(_render_row((field, _escape_cell(values[field]))) for field in CAPSULE_FIELDS)
    bounds = _section_bounds(lines, CAPSULE_HEADING)
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block)
    else:
        start, end = bounds
        lines[start:end] = block + ([""] if end < len(lines) else [])
    return lines


def capsule_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    table = parse_table(text)
    _require_v2(table)
    lines = text.splitlines()
    bounds = _section_bounds(lines, CAPSULE_HEADING)
    if bounds is None:
        raise ValueError("compact capsule section is missing")
    start, end = bounds
    section = NL.join(lines[start:end]).rstrip()
    hash_match = re.search(r"상황판 SHA-256\*\*: `([0-9A-F]{64})`", section)
    if hash_match is None:
        raise ValueError("compact capsule has no board hash")
    actual = _board_sha(lines, table)
    if hash_match.group(1) != actual:
        raise ValueError(f"STALE_CAPSULE expected={hash_match.group(1)} actual={actual}")
    for field in CAPSULE_FIELDS:
        if not re.search(rf"(?m)^\| {re.escape(field)} \| \S", section):
            raise ValueError(f"compact capsule field missing or empty: {field}")
    if len(section) > 6000:
        raise ValueError(f"compact capsule exceeds 6000 characters: {len(section)}")
    return section


def _atomic_write(path: Path, original: bytes, text: str) -> None:
    lock = path.with_name(path.name + ".lock")
    lock_fd: int | None = None
    lock_acquired = False
    temp_name: str | None = None
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        lock_acquired = True
        os.write(lock_fd, f"pid={os.getpid()} time={_now()}\n".encode("utf-8"))
        os.close(lock_fd)
        lock_fd = None
        if path.read_bytes() != original:
            raise RuntimeError("ledger changed after read; no write performed")
        data = (text.rstrip() + NL).encode("utf-8")
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=path.name + ".", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temp_name = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        if lock_acquired:
            lock.unlink(missing_ok=True)


def _mutate(path: Path, mutator) -> None:
    original = path.read_bytes()
    text = original.decode("utf-8")
    lines = text.splitlines()
    mutator(lines, text)
    refresh_capsule(path, lines)
    _atomic_write(path, original, NL.join(lines))


def _find_item(table: Table, item_id: str) -> tuple[int, list[str]]:
    hits = [(index, cells) for index, found, cells in table.rows if found == item_id]
    if len(hits) != 1:
        raise ValueError(f"item {item_id} must occur exactly once, found={len(hits)}")
    return hits[0]


def set_state(
    path: Path,
    item_id: str,
    status: str,
    note: str,
    artifact: str | None,
    resume: str | None,
) -> tuple[str, str]:
    result: dict[str, str] = {}

    def mutate(lines: list[str], text: str) -> None:
        table = parse_table(text)
        _require_v2(table)
        index, cells = _find_item(table, item_id)
        previous = cells[2]
        if DONE in previous:
            raise ValueError("completed item cannot be reopened")
        allowed = {
            RUN: (WAIT, BLOCK),
            DONE: (RUN,),
            WAIT: (RUN, BLOCK),
            BLOCK: (WAIT, RUN),
        }
        if not any(mark in previous for mark in allowed[status]):
            raise ValueError(f"invalid transition {previous} -> {status}")
        if status != DONE and (resume is None or not resume.strip()):
            raise ValueError("--resume is required for start/wait/block")
        cells[2] = status
        cells[3] = _escape_cell(note)
        if artifact is not None:
            cells[4] = _escape_cell(artifact)
        cells[5] = "—" if status == DONE else _escape_cell(resume or "")
        lines[index] = _render_row(cells)
        stamp = {WAIT: "대기", RUN: "착수", DONE: "완료", BLOCK: "막힘"}[status]
        _append_to_section(
            lines,
            LOG_HEADING,
            [f"- `{_now()}` **{item_id}번 {stamp}** — {cells[3]}; 산출물={cells[4]}; 이어받기={cells[5]}"],
        )
        result.update(previous=previous, current=status)

    _mutate(path, mutate)
    return result["previous"], result["current"]


def add_item(path: Path, item_id: str, directive: str, resume: str) -> None:
    def mutate(lines: list[str], text: str) -> None:
        table = parse_table(text)
        _require_v2(table)
        if any(found == item_id for _, found, _ in table.rows):
            raise ValueError(f"item already exists: {item_id}")
        insertion = table.header_index + 2 + len(table.rows)
        lines.insert(
            insertion,
            _render_row((f"**{item_id}**", _escape_cell(directive), WAIT, "—", "—", _escape_cell(resume))),
        )
        _append_to_section(
            lines,
            LOG_HEADING,
            [f"- `{_now()}` **{item_id}번 추가** — 사용자 지시={_escape_cell(directive)}; 이어받기={_escape_cell(resume)}"],
        )

    _mutate(path, mutate)


def override_field(
    path: Path,
    item_id: str,
    field: str,
    expect_before: str,
    set_after: str,
    reason: str,
    approval_ref: str,
    allow_directive_correction: bool,
) -> None:
    mapping = {"사용자 지시": 1, "상태": 2, "작업 내용": 3, "산출물": 4, "이어받을 지점": 5}
    if field not in mapping:
        raise ValueError(f"unsupported override field: {field}")
    if field == "상태":
        raise ValueError("status override is forbidden; use a normal transition")
    if field == "사용자 지시" and not allow_directive_correction:
        raise ValueError("directive correction requires --allow-directive-correction")
    if not reason.strip() or not approval_ref.strip():
        raise ValueError("--reason and --approval-ref are required")

    def mutate(lines: list[str], text: str) -> None:
        table = parse_table(text)
        _require_v2(table)
        index, cells = _find_item(table, item_id)
        column = mapping[field]
        current = cells[column]
        if current != expect_before:
            raise ValueError(
                f"STALE_BEFORE item={item_id} field={field!r} expected={expect_before!r} actual={current!r}"
            )
        after = _escape_cell(set_after)
        cells[column] = after
        lines[index] = _render_row(cells)
        record = {
            "change_id": f"WIP-{dt.datetime.now().astimezone():%Y%m%dT%H%M%S%z}-{item_id}",
            "timestamp": _now(),
            "item": item_id,
            "field": field,
            "before": current,
            "before_sha256": _sha_text(current),
            "after": after,
            "after_sha256": _sha_text(after),
            "reason": reason.strip(),
            "approval_ref": approval_ref.strip(),
            "operation": "compare-and-set single field",
            "cli_contract": [
                "scripts/wip.py",
                "--override",
                "--file",
                "<ledger>",
                "--item",
                item_id,
                "--field",
                field,
                "--expect-before",
                "<redacted: exact value retained in before>",
                "--set-after",
                "<redacted: exact value retained in after>",
                "--reason",
                "<redacted: retained in reason>",
                "--approval-ref",
                "<redacted: retained in approval_ref>",
            ],
        }
        payload = json.dumps(record, ensure_ascii=False, indent=2)
        _append_to_section(lines, AUDIT_HEADING, ["```json", *payload.splitlines(), "```"])

    _mutate(path, mutate)


def bind_session(path: Path, session_id: str, reason: str, approval_ref: str) -> None:
    """Bind an older unbound open v2 ledger to its owning Codex session."""

    if path.name.endswith("-done.md"):
        raise ValueError("completed ledgers are immutable and cannot be session-bound")
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", session_id.strip()):
        raise ValueError("--bind-session requires a nonempty safe --session-id")
    if not reason.strip() or not approval_ref.strip():
        raise ValueError("--bind-session requires --reason and --approval-ref")

    def mutate(lines: list[str], text: str) -> None:
        table = parse_table(text)
        _require_v2(table)
        if _metadata(text, "Codex 세션 ID", ""):
            raise ValueError("ledger already has a Codex session ID")
        schema_rows = [
            index for index, line in enumerate(lines)
            if line.startswith("- **WIP 스키마**:")
        ]
        if len(schema_rows) != 1:
            raise ValueError(f"WIP schema metadata count must be 1: {len(schema_rows)}")
        value = session_id.strip()
        lines.insert(schema_rows[0] + 1, f"- **Codex 세션 ID**: `{value}`")
        record = {
            "change_id": f"WIP-{dt.datetime.now().astimezone():%Y%m%dT%H%M%S%z}-SESSION",
            "timestamp": _now(),
            "before": "(missing)",
            "before_sha256": _sha_text("(missing)"),
            "after": value,
            "after_sha256": _sha_text(value),
            "reason": reason.strip(),
            "approval_ref": approval_ref.strip(),
            "operation": "bind previously unbound open ledger to owning Codex session",
            "cli_contract": [
                "scripts/wip.py",
                "--bind-session",
                "--file",
                "<ledger>",
                "--session-id",
                "<owning session id>",
                "--reason",
                "<redacted: retained in reason>",
                "--approval-ref",
                "<redacted: retained in approval_ref>",
            ],
        }
        payload = json.dumps(record, ensure_ascii=False, indent=2)
        _append_to_section(lines, AUDIT_HEADING, ["```json", *payload.splitlines(), "```"])

    _mutate(path, mutate)


def migrate_v2(path: Path, approval_ref: str, user_owned: str, retired_claims: str) -> None:
    original = path.read_bytes()
    text = original.decode("utf-8")
    table = parse_table(text)
    if table.is_v2:
        raise ValueError("ledger is already v2")
    if not approval_ref.strip():
        raise ValueError("--approval-ref is required for migration")
    if path.name.endswith("-done.md"):
        raise ValueError("completed ledgers are immutable and cannot be migrated")
    lines = text.splitlines()
    old_header = list(table.header)
    converted: list[str] = []
    for _, item_id, old in table.rows:
        values = dict(zip(old_header, old))
        directive = values.get("사용자 지시", values.get("지시", "—"))
        state = values.get("상태", WAIT)
        work = values.get("작업 내용", "—")
        artifact = values.get("산출물", "—")
        old_resume = values.get("이어받을 지점", "")
        if DONE in state or BLOCK in state:
            resume = "—"
        elif old_resume and old_resume != "—":
            resume = old_resume
        elif RUN in state:
            resume = "현재 작업 내용에서 다음 검증 단계로 재개"
        else:
            resume = "사용자 지시 셀의 작업에 착수"
        converted.append(_render_row((f"**{item_id}**", directive, state, work, artifact, resume)))
    lines[table.header_index] = _render_row(V2_HEADER)
    lines[table.header_index + 1] = _render_row(("---", "---", "---", "---", "---", "---"))
    first_row = table.header_index + 2
    lines[first_row : first_row + len(table.rows)] = converted
    if "- **WIP 스키마**:" not in text:
        insert_at = next((i for i, line in enumerate(lines) if line.startswith("## ")), 1)
        lines[insert_at:insert_at] = [
            "- **WIP 스키마**: `v2`",
            f"- **사용자 소유 실행**: {_escape_cell(user_owned)}",
            f"- **폐기·정정 주장**: {_escape_cell(retired_claims)}",
            "",
        ]
    if _section_bounds(lines, AUDIT_HEADING) is None:
        lines.extend(("", AUDIT_HEADING, ""))
    record = {
        "change_id": f"WIP-{dt.datetime.now().astimezone():%Y%m%dT%H%M%S%z}-schema",
        "timestamp": _now(),
        "operation": "legacy-to-v2 schema migration",
        "before_header": old_header,
        "after_header": list(V2_HEADER),
        "before_file_sha256": _sha_bytes(original),
        "approval_ref": approval_ref.strip(),
        "note": "completed ledgers were not changed; open ledger only",
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2)
    _append_to_section(lines, AUDIT_HEADING, ["```json", *payload.splitlines(), "```"])
    refresh_capsule(path, lines)
    _atomic_write(path, original, NL.join(lines))


def show(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    table = parse_table(text)
    prefix = "WIP_V2" if table.is_v2 else "LEGACY_READ_ONLY"
    print("=" * 104)
    print(f"  {prefix} {path.name} — 항목 {len(table.rows)}개")
    print("=" * 104)
    open_count = 0
    for _, item_id, cells in table.rows:
        status = cells[2]
        if any(mark in status for mark in OPEN_MARKS):
            open_count += 1
        directive = re.sub(r"\s+", " ", cells[1])[:52]
        work = re.sub(r"\s+", " ", cells[3] if table.is_v2 else cells[-2])[:38]
        print(f"  {item_id:>3}  {status:<10}  {directive:<54}  {work}")
    print(f"\n  열린 항목 {open_count}개 · 닫힌 항목 {len(table.rows) - open_count}개")
    if not table.is_v2:
        print("  LEGACY_READ_ONLY: 상태 변경·닫기 금지")
    return open_count


def close(path: Path) -> Path:
    text = path.read_text(encoding="utf-8")
    table = parse_table(text)
    _require_v2(table)
    open_items = [item_id for _, item_id, cells in table.rows if any(mark in cells[2] for mark in OPEN_MARKS)]
    if open_items:
        raise ValueError(f"열린 항목 {len(open_items)}개: {', '.join(open_items)}")
    elided = [item_id for _, item_id, cells in table.rows if any(x in cells[1] for x in ("(…)", "(...)"))]
    if elided:
        raise ValueError(f"지시 원문 생략 표식이 남음: {', '.join(elided)}")
    capsule_text(path)
    target = path.with_name(path.stem + "-done.md")
    if target.exists():
        raise ValueError(f"close target already exists: {target.name}")
    path.replace(target)
    return target


def _closed_ledger_path(path: Path) -> Path:
    return path.with_name(path.stem + "-done.md")


def _ledger_slot_taken(path: Path) -> bool:
    return path.exists() or _closed_ledger_path(path).exists()


def _next_ledger_path() -> Path:
    day = dt.datetime.now().strftime("%Y%m%d")
    base = HANDOFF / f"WIP_{day}_작업원장.md"
    if not _ledger_slot_taken(base):
        return base
    for offset in range(1, 27):
        suffix = chr(ord("a") + offset)
        candidate = HANDOFF / f"WIP_{day}{suffix}_작업원장.md"
        if not _ledger_slot_taken(candidate):
            return candidate
    raise ValueError("same-day WIP suffix space exhausted")


def repair_name_collision(path: Path, reason: str, approval_ref: str) -> Path:
    """Move an open ledger whose eventual ``-done`` target already exists."""

    if not reason.strip() or not approval_ref.strip():
        raise ValueError("--repair-name-collision requires --reason and --approval-ref")
    text = path.read_text(encoding="utf-8")
    table = parse_table(text)
    _require_v2(table)
    collision = _closed_ledger_path(path)
    if not collision.exists():
        raise ValueError(f"no close-target collision: {collision.name}")
    target = _next_ledger_path()
    if _ledger_slot_taken(target):
        raise ValueError(f"repair target already exists: {target.name}")

    original = path.read_bytes()
    lines = text.splitlines()
    record = {
        "change_id": f"WIP-{dt.datetime.now().astimezone():%Y%m%dT%H%M%S%z}-NAME",
        "timestamp": _now(),
        "before": path.name,
        "before_sha256": _sha_text(path.name),
        "after": target.name,
        "after_sha256": _sha_text(target.name),
        "reason": reason.strip(),
        "approval_ref": approval_ref.strip(),
        "operation": "repair open-ledger close-target name collision",
        "cli_contract": [
            "scripts/wip.py",
            "--repair-name-collision",
            "--file",
            "<ledger>",
            "--reason",
            "<redacted: retained in reason>",
            "--approval-ref",
            "<redacted: retained in approval_ref>",
        ],
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2)
    _append_to_section(lines, AUDIT_HEADING, ["```json", *payload.splitlines(), "```"])
    refresh_capsule(target, lines)
    _atomic_write(path, original, NL.join(lines))
    if _ledger_slot_taken(target):
        raise RuntimeError(f"repair target appeared during write: {target.name}")
    path.rename(target)
    return target


def create_ledger(
    items: list[str],
    previous: str,
    allowlist: str,
    not_run: str,
    user_owned: str,
    retired_claims: str,
    *,
    allow_concurrent: bool = False,
    concurrent_reason: str = "",
    session_id: str = "",
) -> Path:
    existing = find_ledgers()
    if existing and not allow_concurrent:
        raise ValueError("an open WIP already exists; close it before creating another")
    if allow_concurrent and not existing:
        raise ValueError("--allow-concurrent requires at least one existing open WIP")
    if allow_concurrent and not concurrent_reason.strip():
        raise ValueError("--allow-concurrent requires --concurrent-reason")
    if allow_concurrent and not session_id.strip():
        raise ValueError("--allow-concurrent requires --session-id or CODEX_SESSION_ID")
    parsed: list[tuple[str, str]] = []
    for raw in items:
        if "=" not in raw:
            raise ValueError("--item format must be ID=directive")
        item_id, directive = raw.split("=", 1)
        item_id = item_id.strip()
        if not re.fullmatch(r"\d+[A-Za-z]?", item_id) or not directive.strip():
            raise ValueError(f"invalid --item: {raw}")
        parsed.append((item_id, directive.strip()))
    if not parsed or len({item_id for item_id, _ in parsed}) != len(parsed):
        raise ValueError("at least one unique --item is required")
    path = _next_ledger_path()
    today = dt.datetime.now().date().isoformat()
    lines = [
        f"# WIP 작업원장 — {today} 세션",
        "",
        f"- **세션 시작**: {today}",
        f"- **직전 핸드오프**: `{_escape_cell(previous)}`",
        f"- **사용자 지시**: {len(parsed)}건(아래 표가 정본)",
        "- **WIP 스키마**: `v2`",
        *([f"- **Codex 세션 ID**: `{_escape_cell(session_id)}`"] if session_id.strip() else []),
        *(
            [
                "- **동시 WIP 생성 승인**: "
                f"{_escape_cell(concurrent_reason)}; 기존 열린 원장: "
                + ", ".join(f"`{path.name}`" for path in existing)
            ]
            if allow_concurrent
            else []
        ),
        f"- **변경 허용 범위**: {_escape_cell(allowlist)}",
        f"- **NOT_RUN 경계**: {_escape_cell(not_run)}",
        f"- **사용자 소유 실행**: {_escape_cell(user_owned)}",
        f"- **폐기·정정 주장**: {_escape_cell(retired_claims)}",
        "",
        BOARD_HEADING,
        "",
        _render_row(V2_HEADER),
        _render_row(("---", "---", "---", "---", "---", "---")),
    ]
    for item_id, directive in parsed:
        lines.append(
            _render_row((f"**{item_id}**", _escape_cell(directive), WAIT, "—", "—", "사용자 지시 셀의 작업에 착수"))
        )
    lines.extend(
        (
            "",
            "범례: ⏳대기 · 🔄진행 · ✅**완료** · 🚫**막힘**(사유 기재)",
            "",
            "## 2. 확보한 수치",
            "",
            "| 구분 | 값 | 근거 |",
            "|---|---:|---|",
            "",
            LOG_HEADING,
            "",
            f"- `{_now()}` 착수. 사용자 지시 {len(parsed)}건을 원문 의미대로 분리했다.",
            "",
            AUDIT_HEADING,
            "",
        )
    )
    refresh_capsule(path, lines)
    data = (NL.join(lines).rstrip() + NL).encode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=path.name + ".", suffix=".tmp", dir=path.parent, delete=False
    ) as stream:
        temp_name = stream.name
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if path.exists():
            raise ValueError(f"refusing to overwrite: {path.name}")
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return path


def main() -> int:
    _configure_utf8_streams()
    parser = argparse.ArgumentParser(description="WIP v2 ledger writer and validator")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list", action="store_true")
    action.add_argument("--new", action="store_true")
    action.add_argument("--add")
    action.add_argument("--start")
    action.add_argument("--done")
    action.add_argument("--block")
    action.add_argument("--wait")
    action.add_argument("--override", action="store_true")
    action.add_argument("--bind-session", action="store_true")
    action.add_argument("--migrate-v2", action="store_true")
    action.add_argument("--capsule-check", action="store_true")
    action.add_argument("--capsule-print", action="store_true")
    action.add_argument("--repair-name-collision", action="store_true")
    action.add_argument("--close", action="store_true")
    parser.add_argument("--file")
    parser.add_argument("--note")
    parser.add_argument("--artifact")
    parser.add_argument("--resume")
    parser.add_argument("--directive")
    parser.add_argument("--item", action="append", default=[])
    parser.add_argument("--previous", default="(없음)")
    parser.add_argument("--allow", dest="allowlist", default="사용자 현재 지시의 명시 범위")
    parser.add_argument("--not-run", default="GPU·모델·데이터셋·삭제·Git 외부 변경")
    parser.add_argument("--user-owned", default="없음으로 기록됨")
    parser.add_argument("--retired-claims", default="없음으로 기록됨")
    parser.add_argument("--field")
    parser.add_argument("--expect-before")
    parser.add_argument("--set-after")
    parser.add_argument("--reason")
    parser.add_argument("--approval-ref")
    parser.add_argument("--allow-directive-correction", action="store_true")
    parser.add_argument("--allow-concurrent", action="store_true")
    parser.add_argument("--concurrent-reason")
    parser.add_argument("--session-id", default=os.environ.get("CODEX_SESSION_ID", ""))
    args = parser.parse_args()
    try:
        if (args.allow_concurrent or args.concurrent_reason) and not args.new:
            raise ValueError("--allow-concurrent/--concurrent-reason are valid only with --new")
        if args.new:
            path = create_ledger(
                args.item,
                args.previous,
                args.allowlist,
                args.not_run,
                args.user_owned,
                args.retired_claims,
                allow_concurrent=args.allow_concurrent,
                concurrent_reason=args.concurrent_reason or "",
                session_id=args.session_id,
            )
            print(f"CREATED {path.relative_to(ROOT).as_posix()} schema=v2 items={len(args.item)}")
            return 0
        if args.list and not args.file:
            ledgers = find_ledgers()
            if not ledgers:
                raise ValueError("열려 있는 작업원장이 없다")
            for index, ledger in enumerate(ledgers):
                if index:
                    print()
                show(ledger)
            return 0
        path = resolve_ledger(args.file, allow_multiple_for_list=args.list)
        active = (
            args.add, args.start, args.done, args.block, args.wait, args.override,
            args.bind_session, args.migrate_v2, args.capsule_check, args.capsule_print,
            args.repair_name_collision, args.close,
        )
        if args.list or not any(active):
            show(path)
            return 0
        if args.migrate_v2:
            migrate_v2(path, args.approval_ref or "", args.user_owned, args.retired_claims)
            print(f"MIGRATED {path.relative_to(ROOT).as_posix()} legacy -> v2")
            return 0
        if args.capsule_check or args.capsule_print:
            capsule = capsule_text(path)
            print(capsule if args.capsule_print else f"CAPSULE_OK {path.name} chars={len(capsule)}")
            return 0
        if args.repair_name_collision:
            target = repair_name_collision(path, args.reason or "", args.approval_ref or "")
            print(
                f"REKEYED {path.relative_to(ROOT).as_posix()} -> "
                f"{target.relative_to(ROOT).as_posix()}; audit appended"
            )
            return 0
        if args.bind_session:
            if not args.file:
                raise ValueError("--bind-session requires explicit --file")
            bind_session(path, args.session_id, args.reason or "", args.approval_ref or "")
            print(f"BOUND {path.relative_to(ROOT).as_posix()} session_id={args.session_id}")
            return 0
        if args.close:
            target = close(path)
            print(f"CLOSED {target.relative_to(ROOT).as_posix()}; source preserved by rename")
            return 0
        if args.add:
            if not args.directive or not args.resume:
                raise ValueError("--add requires --directive and --resume")
            add_item(path, args.add, args.directive, args.resume)
            print(f"ADDED {args.add} to {path.name}")
            return 0
        if args.override:
            values = {
                "--item": args.item[0] if len(args.item) == 1 else None,
                "--field": args.field,
                "--expect-before": args.expect_before,
                "--set-after": args.set_after,
                "--reason": args.reason,
                "--approval-ref": args.approval_ref,
            }
            missing = [name for name, value in values.items() if value is None or not str(value).strip()]
            if missing:
                raise ValueError(f"override missing required arguments: {', '.join(missing)}")
            override_field(
                path,
                str(values["--item"]), str(values["--field"]),
                str(values["--expect-before"]), str(values["--set-after"]),
                str(values["--reason"]), str(values["--approval-ref"]),
                args.allow_directive_correction,
            )
            print(f"OVERRIDE_OK item={values['--item']} field={values['--field']}")
            return 0
        item_id, status = (
            (args.start, RUN) if args.start else
            (args.done, DONE) if args.done else
            (args.block, BLOCK) if args.block else
            (args.wait, WAIT)
        )
        if not args.note or not args.note.strip():
            raise ValueError("--note is required for every state change")
        previous, current = set_state(path, str(item_id), status, args.note, args.artifact, args.resume)
        print(f"STATE_OK {item_id}: {previous} -> {current}")
        return 0
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        print(f"WIP_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
