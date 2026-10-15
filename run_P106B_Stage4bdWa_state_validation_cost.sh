#!/usr/bin/env bash
# Read-only selected-parent timing of all exact state development paths; optimizer/CPT0.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bdWa_state_validation_cost_"$stamp" --note 'Exact frozen state development path timing; no optimizer/checkpoint or old evidence changes.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bdWa_state_validation_cost_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_validation_cost.py --variant state --execute --max-wall-sec 900
