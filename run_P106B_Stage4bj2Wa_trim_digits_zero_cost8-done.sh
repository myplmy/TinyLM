#!/usr/bin/env bash
# Actual8 complete state-fixed/digits0 right-trim costs and head postconditions; no checkpoint.
# Independent execution namespace; original producer files and defaults remain unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj2Wa_trim_digits_zero_cost8_"$stamp" --note 'Actual8 complete state-fixed/digits0 right-trim costs and head postconditions; no checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj2Wa_trim_digits_zero_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_trim.py --mode cost --arm digits0 --execute --max-wall-sec 900
