#!/usr/bin/env python3
"""P106B Stage1fW: user-run full-16 teacher correction candidate census.

The previous three-case repair gate is only a prompt/format fixture. This
stage generates a new immutable v4 candidate set for all pinned sixteen,
without automatically accepting any teacher answer or training a student.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.diag_p106b_teacher_answer_repair import (
    CTX, FULL_MANIFEST, FULL_OUTPUT, FULL_WALL_LIMIT, MAX_TOKENS, SAMPLER,
    THINKING_BUDGET, execute, full_source_cases, self_test,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            print("[PASS] full16 wrapper keeps all candidates unaccepted; model/GPU NOT_RUN")
            return 0
        cases, source = full_source_cases()
        if args.check_only:
            print(json.dumps({"source": source, "cases": len(cases),
                              "ctx": CTX, "max_tokens": MAX_TOKENS,
                              "thinking_budget_tokens": THINKING_BUDGET,
                              "sampler": SAMPLER,
                              "new_output": FULL_OUTPUT.as_posix(),
                              "student_training": "NOT_RUN"}, sort_keys=True))
            print("[CHECK_ONLY] pinned v1/v2/v3 lineage PASS; teacher/model/GPU NOT_RUN")
            return 0
        def time_limit(_signum, _frame):
            raise TimeoutError("P106B Stage1fW full16 hard wall 3300s")
        previous = signal.signal(signal.SIGALRM, time_limit)
        signal.alarm(3300)
        try:
            return execute(cases, source, output=FULL_OUTPUT, manifest=FULL_MANIFEST,
                           wall_limit=FULL_WALL_LIMIT, min_complete=12,
                           schema="P106B_STAGE1FW_TEACHER_REPAIR_FULL16_V1")
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f"[FAIL] P106B Stage1fW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
