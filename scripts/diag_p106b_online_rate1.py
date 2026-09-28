#!/usr/bin/env python3
"""P106B Stage2iWd: one-update backend/format recovery on old OASST1 pool.

This is a user-run co-resident diagnostic after Stage2fWb, not a replacement
for the separate OASST2/Aya/dictionary data-source decision or a quality run.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys

from diag_p106b_online_rate5 import check_only, execute, paths, self_test, PrerequisiteHold

WALL_LIMIT = 5400


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
            assert paths("low", "backend1")[0].name == "v13_online_rate1_low_backend"
            print("[PASS] new write-once backend1 output, one update only; model/GPU NOT_RUN")
        elif args.check_only:
            print(json.dumps(check_only("low", "backend1"), ensure_ascii=False, sort_keys=True))
            print("[CHECK_ONLY] Stage2fWb/parent/source PASS; model/GPU NOT_RUN")
        else:
            def time_limit(_signum, _frame):
                raise TimeoutError("P106B Stage2iWd 1-update hard wall")
            old = signal.signal(signal.SIGALRM, time_limit)
            signal.alarm(WALL_LIMIT + 180)
            try:
                return execute("low", WALL_LIMIT, "backend1")
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
        return 0
    except PrerequisiteHold as exc:
        print(f"[HOLD] P106B Stage2iWd {exc}; student GPU NOT_RUN")
        return 8
    except (OSError, ValueError, RuntimeError, TimeoutError, TypeError, KeyError) as exc:
        print(f"[FAIL] P106B Stage2iWd {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
