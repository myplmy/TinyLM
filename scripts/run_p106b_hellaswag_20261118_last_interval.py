"""Run one remaining official prefix interval inside the 17:00 authorization."""

import argparse
from datetime import datetime
import json
from pathlib import Path

from scripts import diag_p106b_bonsai_hellaswag_exact_intervals as stage


TAG = "p106b_bonsai_hellaswag_exact_prefix_last_interval_20261118"
ROOT = stage.io.ROOT
READBACK = ROOT / "handoff/audit/research_20261118_01a1e647/BONSAI_HELLASWAG_INTERVALS_COMBINED_CPU_READBACK_v1.json"
EVIDENCE = ROOT / "test_result/evidence"
RECEIPTS = tuple(EVIDENCE / (tag + "_20261118") / "terminal.json" for tag in (
    "p106b_bonsai_hellaswag_exact_prefix_intervals_v1",
    "p106b_bonsai_hellaswag_exact_prefix_continue_v1",
))
FIRST, END = 2816, 2912
CUTOFF = "2026-11-18T16:59:40+09:00"
saved_fingerprint = stage.fingerprint
stage.TAG = TAG
stage.OUT = EVIDENCE / TAG
stage.PROFILE = stage.OUT / "profile.json"
stage.RANGES = ((FIRST, END),)
stage.CAP = 245
stage.core.CUTOFF = datetime.fromisoformat(CUTOFF).timestamp()


def fingerprint():
    profile, previous, native = saved_fingerprint()
    readback = json.loads(READBACK.read_bytes())
    assert readback["next_official_ordinal"] == readback["distinct_rows"] == FIRST
    assert readback["remaining"] == profile["rows_total"] - FIRST
    assert readback["source"] == profile["official"] and readback["duplicate_rows"] == 0
    assert len(readback["children"]) == len(RECEIPTS) == 2
    cursor = 0
    for child, path in zip(readback["children"], RECEIPTS, strict=True):
        assert child["exit"] == 0 and child["terminal_sha256"] == stage.io.digest(path)
        state = json.loads(path.read_bytes())
        assert state["release"]["competing_compute_pids"] == [] and state["handles_closed"]
        for record in state["intervals"]:
            assert record["first"] == cursor and record["complete_interval"]
            manifest = record["manifest"]
            directory = path.parent / f"rows_{cursor:05}_{record['end_exclusive']:05}"
            stage.core.verify_shards(directory, manifest)
            cursor += manifest["rows"]
            assert cursor == record["end_exclusive"]
    assert cursor == FIRST
    profile.update(cutoff_KST=CUTOFF, previous_cpu_sha256=stage.io.digest(READBACK),
                   launcher_sha256=stage.io.digest(Path(__file__)))
    return profile, previous, native


stage.fingerprint = fingerprint


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "actual"))
    raise SystemExit(stage.actual() if parser.parse_args().mode == "actual" else stage.prepare())
