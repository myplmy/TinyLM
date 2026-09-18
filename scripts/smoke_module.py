#!/usr/bin/env python3
"""Run the canonical smoke BAT module on POSIX without duplicating its arm list.

Only the narrow command grammar owned by scripts/batch/tool_smoke.bat is
accepted. Unknown executable syntax fails during parsing, so a future BAT edit
cannot be silently skipped by the WSL path. --check parses only and never loads
models or executes smoke arms.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "scripts" / "batch" / "tool_smoke.bat"


@dataclass(frozen=True)
class Action:
    kind: str
    line: int
    argv: tuple[str, ...] = ()
    seconds: int = 0


def _runlog_action(line: str, line_number: int, log_name: str) -> Action:
    normalized = line.replace("\\", "/")
    tokens = shlex.split(normalized, posix=True)
    if len(tokens) < 2 or tokens[0].lower() != "python":
        raise ValueError(f"line {line_number}: malformed Python invocation")
    if tokens[1].lower() != "scripts/runlog.py":
        raise ValueError(f"line {line_number}: only scripts/runlog.py is executable")

    tokens[0] = sys.executable
    tokens = [log_name if token == "!TL_LOGNAME!" else token for token in tokens]
    if "--" in tokens:
        separator = tokens.index("--")
        if separator + 1 >= len(tokens):
            raise ValueError(f"line {line_number}: runlog command has an empty child")
        if tokens[separator + 1].lower() != "python":
            raise ValueError(
                f"line {line_number}: runlog child must start with the selected Python"
            )
        tokens[separator + 1] = sys.executable
    return Action("run", line_number, tuple(tokens))


def parse_smoke_module(
    path: Path = DEFAULT_SOURCE, *, log_name: str = "smoke"
) -> list[Action]:
    actions: list[Action] = []
    for line_number, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        line = raw.strip()
        lowered = line.lower()
        if not line or lowered == "rem" or lowered.startswith("rem ") or line.startswith("::"):
            continue
        if lowered.startswith("python scripts\\runlog.py"):
            actions.append(_runlog_action(line, line_number, log_name))
            continue
        if lowered == "timeout /t 15 /nobreak":
            actions.append(Action("sleep", line_number, seconds=15))
            continue

        allowed_nonexecuting = (
            lowered == "@echo off"
            or lowered == "setlocal enabledelayedexpansion"
            or lowered.startswith("if not exist run100m.py ")
            or lowered.startswith("if not defined tl_outdir set ")
            or lowered.startswith("if not defined tl_logname set ")
            or lowered.startswith("if errorlevel 1 echo ")
            or lowered.startswith("if not defined tl_nopause pause")
            or lowered.startswith("echo")
            or lowered.startswith("goto ")
            or lowered.startswith(":")
            or lowered.startswith("exit /b ")
        )
        if allowed_nonexecuting:
            continue
        raise ValueError(
            f"line {line_number}: unsupported BAT statement for POSIX smoke: {line}"
        )
    if not any(action.kind == "run" for action in actions):
        raise ValueError("smoke module contains no runlog action")
    return actions


def execute(actions: list[Action], *, log_name: str) -> int:
    env = os.environ.copy()
    env.setdefault("TL_OUTDIR", "smoketest_logs")
    env["TL_LOGNAME"] = log_name
    env["TL_NOPAUSE"] = "1"

    nonzero = 0
    for action in actions:
        if action.kind == "sleep":
            time.sleep(action.seconds)
            continue
        completed = subprocess.run(action.argv, cwd=ROOT, env=env, check=False)
        if completed.returncode != 0:
            nonzero += 1
            print(
                f"[WARN] smoke source line {action.line} returned "
                f"{completed.returncode}; continuing for final summary",
                file=sys.stderr,
            )
    print(f"[smoke-posix] actions={len(actions)} nonzero_runlog_calls={nonzero}")
    # The canonical BAT module also returns zero after all arms. summarize_smoke.py
    # owns the joined verdict and is invoked by run_smoke_check.sh.
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--name", default="smoke")
    parser.add_argument(
        "--check",
        action="store_true",
        help="strictly parse the BAT module without executing any action",
    )
    args = parser.parse_args()

    try:
        actions = parse_smoke_module(args.source, log_name=args.name)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"[FAIL] smoke module parse: {exc}", file=sys.stderr)
        return 2

    if args.check:
        runs = sum(action.kind == "run" for action in actions)
        sleeps = sum(action.kind == "sleep" for action in actions)
        print(f"[PASS] smoke module grammar: runlog={runs} sleep={sleeps}")
        return 0
    return execute(actions, log_name=args.name)


if __name__ == "__main__":
    sys.exit(main())
