#!/usr/bin/env python3
"""Regression tests for valid ANSI CSI versus accidental control bytes."""
from __future__ import annotations

from check_control_chars import first_bad_control


def main() -> int:
    assert first_bad_control(b"plain text\n") is None
    assert first_bad_control(b"\x1b[1;34mwandb\x1b[0m: run\n") is None
    print("[PASS] plain text and complete ANSI CSI sequences are accepted")

    assert first_bad_control(b"broken \x1b text") == (7, 0x1B)
    assert first_bad_control(b"broken \x1b[31") == (7, 0x1B)
    print("[PASS] isolated and incomplete ESC sequences are rejected")

    assert first_bad_control(b"scripts\batch") == (7, 0x08)
    print("[PASS] accidental backspace remains rejected")
    print("[PASS] control character regression 3/3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
