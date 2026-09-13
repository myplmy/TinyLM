#!/usr/bin/env python3
"""Lossless handoff queue inheritance and validation helper.

It reads only the named handoff document, root ``experiments.tsv`` and root
``run_*.bat`` inventory through ``queue_menu.py``.  It never builds or executes a
queue.  Scientific priority and readiness remain human/agent judgments; generated
rows therefore default to ``REVALIDATE``.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
HANDOFF = ROOT / "handoff"
QUEUE_MODULE = ROOT / "scripts" / "queue_menu.py"

QUEUE_COLUMNS = (
    "순",
    "id",
    "실험",
    "배치 파일",
    "⚙",
    "누적",
    "인벤토리",
    "실행상태",
    "선결",
    "근거",
)
INVENTORY_STATES = {"PRESENT", "DONE", "MISSING", "REPLACED"}
EXECUTION_STATES = {"READY", "GATED", "HOLD", "DONE", "REVALIDATE"}


@dataclass(frozen=True)
class QueueItem:
    batch: str
    experiment: str
    precondition: str
    reason: str
    execution: str


def _cells(line: str) -> list[str]:
    raw = re.split(r"(?<!\\)\|", line.strip())
    if raw and raw[0] == "":
        raw = raw[1:]
    if raw and raw[-1] == "":
        raw = raw[:-1]
    return [cell.strip().replace(r"\|", "|") for cell in raw]


def _section(text: str, number: str = "7") -> str:
    match = re.search(rf"(?m)^##\s*{re.escape(number)}\..*$", text)
    if match is None:
        return ""
    following = text[match.end() :]
    next_heading = re.search(r"(?m)^##\s", following)
    return following[: next_heading.start() if next_heading else None]


def _tables(section: str) -> list[tuple[list[str], list[list[str]]]]:
    lines = section.splitlines()
    tables: list[tuple[list[str], list[list[str]]]] = []
    index = 0
    while index + 1 < len(lines):
        if not lines[index].lstrip().startswith("|") or not re.match(
            r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", lines[index + 1]
        ):
            index += 1
            continue
        header = _cells(lines[index])
        rows: list[list[str]] = []
        index += 2
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            cells = _cells(lines[index])
            if len(cells) == len(header):
                rows.append(cells)
            index += 1
        tables.append((header, rows))
    return tables


def queue_items(text: str) -> list[QueueItem]:
    for header, rows in _tables(_section(text)):
        batch_column = next((i for i, name in enumerate(header) if "배치" in name), None)
        if batch_column is None or "실험" not in header:
            continue
        experiment_column = header.index("실험")
        precondition_column = header.index("선결") if "선결" in header else None
        reason_column = header.index("근거") if "근거" in header else None
        execution_column = header.index("실행상태") if "실행상태" in header else None
        items: list[QueueItem] = []
        for row in rows:
            batch = row[batch_column].strip(" `")
            if not batch.lower().endswith(".bat"):
                continue
            execution = row[execution_column] if execution_column is not None else "REVALIDATE"
            items.append(
                QueueItem(
                    batch=batch,
                    experiment=row[experiment_column],
                    precondition=row[precondition_column] if precondition_column is not None else "재검증",
                    reason=row[reason_column] if reason_column is not None else "직전 핸드오프에서 계승",
                    execution=execution,
                )
            )
        return items
    return []


def transferred_batches(text: str) -> set[str]:
    section = _section(text)
    for header, rows in _tables(section):
        if "이전 배치" not in header or "처리" not in header or "근거" not in header:
            continue
        batch_column = header.index("이전 배치")
        return {
            row[batch_column].strip(" `")
            for row in rows
            if row[batch_column].strip(" `").lower().endswith(".bat")
            and row[header.index("처리")].strip()
            and row[header.index("근거")].strip()
        }
    return set()


def _load_registry() -> tuple[list[dict[str, object]], list[str]]:
    spec = importlib.util.spec_from_file_location("tinylm_queue_for_handoff", QUEUE_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {QUEUE_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load()


def inherited_rows(previous: Path) -> list[str]:
    items = [item for item in queue_items(previous.read_text(encoding="utf-8")) if item.execution != "DONE"]
    rows, warnings = _load_registry()
    if warnings:
        raise ValueError("experiments.tsv warning: " + " | ".join(warnings))
    available = [row for row in rows if bool(row["exists"])]
    live_id = {str(row["batch"]): index for index, row in enumerate(available)}
    by_batch = {str(row["batch"]): row for row in rows}
    rendered: list[str] = []
    cumulative = 0.0
    for priority, item in enumerate(items, start=1):
        registry = by_batch.get(item.batch)
        if item.batch in live_id and registry is not None:
            inventory, execution = "PRESENT", "REVALIDATE"
            queue_id = str(live_id[item.batch])
            hours = float(registry["hours_n"])
        elif registry is not None and bool(registry["done"]):
            inventory, execution = "DONE", "DONE"
            queue_id = "—"
            hours = float(registry["hours_n"])
        else:
            inventory, execution = "MISSING", "HOLD"
            queue_id = "—"
            hours = float(registry["hours_n"]) if registry is not None else 0.0
        cumulative += hours
        reason = re.sub(r"\s+", " ", item.reason).replace("|", r"\|")
        reason = f"직전 핸드오프 계승; {reason}; 현재 과학적 순서 재검증 필요"
        experiment = re.sub(r"\s+", " ", item.experiment).replace("|", r"\|")
        precondition = re.sub(r"\s+", " ", item.precondition).replace("|", r"\|")
        rendered.append(
            f"| {priority} | {queue_id} | {experiment} | `{item.batch}` | {hours:.1f} | "
            f"{cumulative:.1f} | {inventory} | {execution} | {precondition} | {reason} |"
        )
    return rendered


def inheritance_errors(current: Path, previous: Path) -> list[str]:
    prior = {
        item.batch
        for item in queue_items(previous.read_text(encoding="utf-8"))
        if item.execution != "DONE" and "-done" not in item.batch.lower()
    }
    current_text = current.read_text(encoding="utf-8")
    present = {item.batch for item in queue_items(current_text)}
    accounted = present | transferred_batches(current_text)
    return [
        f"previous incomplete queue batch has no current row or transfer reason: {batch}"
        for batch in sorted(prior - accounted)
    ]


def render_table(previous: Path) -> str:
    header = "| " + " | ".join(QUEUE_COLUMNS) + " |"
    separator = "|---:|---:|---|---|---:|---:|---|---|---|---|"
    rows = inherited_rows(previous)
    return "\n".join((header, separator, *rows))


def _resolve_handoff(raw: str) -> Path:
    path = (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    path.relative_to(HANDOFF.resolve())
    if not path.is_file():
        raise ValueError(f"handoff does not exist: {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="handoff queue inheritance helper; never executes batches")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--render", metavar="PREVIOUS_HANDOFF")
    action.add_argument("--audit", metavar="CURRENT_HANDOFF")
    parser.add_argument("--previous", help="previous handoff for --audit")
    args = parser.parse_args()
    try:
        if args.render:
            print(render_table(_resolve_handoff(args.render)))
            return 0
        current = _resolve_handoff(args.audit)
        if not args.previous:
            raise ValueError("--audit requires --previous")
        previous = _resolve_handoff(args.previous)
        errors = inheritance_errors(current, previous)
        for error in errors:
            print(f"FAIL {error}")
        print(f"SUMMARY previous_incomplete={len(queue_items(previous.read_text(encoding='utf-8')))} errors={len(errors)}")
        return 1 if errors else 0
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        print(f"HANDOFF_QUEUE_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
