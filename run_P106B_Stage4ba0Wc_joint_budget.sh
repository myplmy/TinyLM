#!/usr/bin/env bash
# Canonical actual costs/postconditions and p95 pair672 plus evaluation/closure before17.
# Independent outputs. No stdin, implicit resume, source overwrite or inference answer selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ba0Wc_joint_budget_"$stamp" --note 'Canonical actual costs/postconditions and p95 pair672 plus evaluation/closure before17.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ba0Wc_joint_budget_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_decimal.py --mode budget --execute
