#!/usr/bin/env bash
# Same new course and original parent. Actual8 updates with zero auxiliary coefficient, no checkpoint.
# Completed2026-10-15 raw095148 exit0; actual8 cost, no checkpoint or quality claim.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al1W_binding_aux_cost8_"$stamp" --note 'Same new course and original parent. Actual8 updates with zero auxiliary coefficient, no checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al1W_binding_aux_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode cost --arm aux0 --execute --max-wall-sec 600
