#!/usr/bin/env python3
"""Regression: diagnostic run metadata with val_loss=null must not crash preflight."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO

from check_run_registry import cmd_audit, cmd_plan, cmd_tag


def main() -> int:
    diagnostic = {
        "_file": "m100R1c_ko-en_300M_p106b_s2g_tagged_pilot_s1337.json",
        "_name": "m100R1c_ko-en_300M_p106b_s2g_tagged_pilot_s1337",
        "tag": "m100R1c_ko-en_300M_p106b_s2g_tagged_pilot_s1337",
        "data": "ko-en", "steps": 2, "final": {"val_loss": None},
        "quality": "NOT_RUN",
    }
    stream = StringIO()
    with redirect_stdout(stream):
        assert cmd_plan([diagnostic], "P106B tagged pilot") == 0
        assert cmd_tag([diagnostic], "p106b_s2g_tagged_pilot_s1337") == 1
        assert cmd_audit([diagnostic]) == 0
    output = stream.getvalue()
    assert "val NOT_RUN" in output and "tagged_pilot" in output
    assert "2" in output
    print("[PASS] null validation remains NOT_RUN while tag collision and plan lookup work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
