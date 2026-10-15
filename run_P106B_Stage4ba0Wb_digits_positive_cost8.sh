#!/usr/bin/env bash
# Actual8 joint costs: same state active and decimal objective1, no checkpoint.
# Independent outputs. No stdin, implicit resume, source overwrite or inference answer selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ba0Wb_digits_positive_cost8_"$stamp" --note 'Actual8 joint costs: same state active and decimal objective1, no checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ba0Wb_digits_positive_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_decimal.py --mode cost --arm digits1 --execute --max-wall-sec 900
