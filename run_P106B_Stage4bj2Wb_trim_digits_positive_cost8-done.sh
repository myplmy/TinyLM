#!/usr/bin/env bash
# Actual8 complete state-fixed/digits1 right-trim costs; source rows and targets unchanged.
# Independent execution namespace; original producer files and defaults remain unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj2Wb_trim_digits_positive_cost8_"$stamp" --note 'Actual8 complete state-fixed/digits1 right-trim costs; source rows and targets unchanged.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj2Wb_trim_digits_positive_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_trim.py --mode cost --arm digits1 --execute --max-wall-sec 900
