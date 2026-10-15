#!/usr/bin/env bash
# Same fresh parent/data/state objective, four passes672, decimal0, native1; time gated.
# Independent outputs. No stdin, implicit resume, source overwrite or inference answer selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4baWa_state_fixed_digits_zero_"$stamp" --note 'Same fresh parent/data/state objective, four passes672, decimal0, native1; time gated.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4baWa_state_fixed_digits_zero_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_decimal.py --mode train --arm digits0 --execute --max-wall-sec 3600
