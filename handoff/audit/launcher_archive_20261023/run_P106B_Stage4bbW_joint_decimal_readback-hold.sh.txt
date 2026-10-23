#!/usr/bin/env bash
# After both canonical arms: parent/students new2048 integer/state/basic first answers and retained abilities.
# Independent outputs. No stdin, implicit resume, source overwrite or inference answer selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bbW_joint_decimal_readback_"$stamp" --note 'After both canonical arms: parent/students new2048 integer/state/basic first answers and retained abilities.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bbW_joint_decimal_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_decimal.py --mode evaluate --execute --max-wall-sec 1800
