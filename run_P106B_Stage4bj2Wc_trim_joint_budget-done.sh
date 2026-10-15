#!/usr/bin/env bash
# Validation-inclusive measured trim pair672 budget plus eval900/closing2700 before17.
# Independent execution namespace; original producer files and defaults remain unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj2Wc_trim_joint_budget_"$stamp" --note 'Validation-inclusive measured trim pair672 budget plus eval900/closing2700 before17.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj2Wc_trim_joint_budget_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_trim.py --mode budget --execute --max-wall-sec 300
