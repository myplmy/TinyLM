#!/usr/bin/env bash
# Actual8 positive last-turn updated-target bit costs, no checkpoint.
# Independent namespace, no stdin, no implicit resume or old checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aw0Wb_state_positive_cost8_"$stamp" --note 'Actual8 positive last-turn updated-target bit costs, no checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aw0Wb_state_positive_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_state_update_aux.py --mode cost --arm aux100 --execute --max-wall-sec 900
