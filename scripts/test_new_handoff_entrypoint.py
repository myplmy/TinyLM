#!/usr/bin/env python3
"""Regression: the handoff generator must start under Python isolated mode."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("new_handoff.py")


def main() -> int:
    completed = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-B", str(SCRIPT), "--help"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--title" in completed.stdout
    print("PASS new_handoff isolated entrypoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
