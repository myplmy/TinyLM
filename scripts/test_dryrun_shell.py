#!/usr/bin/env python3
"""WSL runlog launchers must be visible to the static experiment preflight."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE = Path(__file__).resolve().with_name("dryrun_batch.py")
SPEC = importlib.util.spec_from_file_location("dryrun_shell_test", MODULE)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def main() -> int:
    shell_train = (
        'exec "$python_bin" scripts/runlog.py --num 090 --name arm -- \\\n'
        '  "$python_bin" run100m.py train --preset m100s10 \\\n'
        '  --tokens 300M --steps 2289 --tag p097_ctrl_v2\n'
    )
    shell_judge = (
        '"$python_bin" scripts/runlog.py --name eval -- \\\n'
        '  "$python_bin" scripts/paired_eval.py --preset m100s8 \\\n'
        '  --models repeated unique --tokens 600M\n'
    )
    batch_train = (
        'python scripts\\runlog.py --name old -- python run100m.py '
        'train --preset m100 --tag old_tag\n'
    )

    shell_calls = list(MOD.launcher_calls(shell_train))
    assert len(shell_calls) == 1
    assert shell_calls[0][0] == "run100m.py"
    assert " ".join(shell_calls[0][1].split()) == (
        "train --preset m100s10 --tokens 300M --steps 2289 --tag p097_ctrl_v2"
    )
    batch_calls = list(MOD.launcher_calls(batch_train))
    assert len(batch_calls) == 1
    assert batch_calls[0][0] == "run100m.py"
    assert " ".join(batch_calls[0][1].split()) == (
        "train --preset m100 --tag old_tag"
    )
    judges = MOD.judge_calls(shell_judge)
    assert len(judges) == 1
    assert judges[0][0] == "paired_eval.py"
    assert " ".join(judges[0][1].split()) == (
        "--preset m100s8 --models repeated unique --tokens 600M"
    )
    print("[PASS] dryrun_batch parses BAT and WSL runlog launchers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
