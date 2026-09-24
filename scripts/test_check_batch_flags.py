#!/usr/bin/env python3
"""BAT runlog child flags belong to the child parser on either path spelling."""
from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_batch_flags as gate


class FakeBat:
    def __init__(self, body):
        self.body = body

    def read_text(self, **_kwargs):
        return self.body


def main():
    def flags(py):
        if py.name == "runlog.py":
            return {"--num", "--name", "--note"}
        if py.name == "diag_m5_dense_bridge.py":
            return {"--platform", "--out"}
        return None

    with patch.object(gate, "declared_flags", side_effect=flags):
        for slash in ("/", chr(92)):
            prefix = f"python scripts{slash}runlog.py --num 095 --name gate -- python -B -X utf8 scripts{slash}diag_m5_dense_bridge.py "
            good = FakeBat(prefix + "--platform windows --out runs/bench/x.json")
            errors, warnings, _ = gate.check(good)
            if errors or warnings:
                raise RuntimeError("child flags misattributed: " + str(errors))
            bad = FakeBat(prefix + "--invented value")
            errors, _, _ = gate.check(bad)
            if len(errors) != 1 or "diag_m5_dense_bridge.py" not in errors[0]:
                raise RuntimeError("invalid child flag was not caught")
        note = FakeBat('python scripts/runlog.py --num 095 --name gate --note "--invented is prose"')
        errors, warnings, _ = gate.check(note)
        if errors or warnings:
            raise RuntimeError("quoted note was parsed as a flag")
    print("[PASS] runlog slash/backslash child flags and invalid flag rejection")


if __name__ == "__main__":
    main()
