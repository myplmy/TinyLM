#!/usr/bin/env python3
"""Stop only the childless owned waiter so its bookkeeping repair can load."""
from pathlib import Path
import hashlib
import json
import os
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_supported_supervisor as supervisor

def main():
    base = Path(__file__).resolve().parent
    script = base / "continue_native_pair.py"
    first = ROOT / "test_result/evidence/p106b_native_format_training_v1_20261026_format_muon_train/root_closed_ref.json"
    if first.exists() or (base / "native_training_cost_admission_v2.json").exists():
        raise ValueError("first closure or second admission already exists; do not stop")
    wanted = [str(script.relative_to(ROOT)), "--execute"]
    expected_exe = Path("/home/uranus/miniforge3/envs/tlm_torch/bin/python").resolve()
    matches = []
    for directory in Path("/proc").iterdir():
        if not directory.name.isdecimal():
            continue
        try:
            if directory.stat().st_uid != os.getuid() or (directory / "cwd").resolve() != ROOT:
                continue
            if (directory / "exe").resolve() != expected_exe:
                continue
            argv = (directory / "cmdline").read_bytes().split(bytes([0]))
            argv = [value.decode() for value in argv if value]
            if argv[-2:] == wanted:
                matches.append((directory, argv, supervisor.proc.proc_stat(int(directory.name))))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    if len(matches) != 1:
        raise ValueError("exact single owned waiter required")
    directory, argv, identity = matches[0]
    children = (directory / "task" / directory.name / "children").read_text().split()
    if children:
        raise ValueError("waiter has started a child; no signal is authorized")
    if supervisor.proc.proc_stat(identity["pid"])["starttime"] != identity["starttime"]:
        raise ValueError("waiter PID reused")
    if first.exists():
        raise ValueError("first closure raced; do not stop")
    os.kill(identity["pid"], signal.SIGTERM)
    value = {"schema": "TINYLM_OWNED_WAITER_RELOAD_V1", "identity": identity, "command": argv,
        "script_sha256_before_repair": hashlib.sha256(script.read_bytes()).hexdigest().upper(),
        "children_before_signal": children, "signal": "SIGTERM", "signal_epoch": time.time(),
        "first_training_signaled": False, "actual_waiter_exit": "ROOT_MUST_COLLECT",
        "reason": "LOAD_TIME_HOLD_BOOKKEEPING_FIX_BEFORE_SECOND_ARM"}
    with (base / "wait_controller_reload_v1.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(value))

if __name__ == "__main__":
    main()
