#!/usr/bin/env bash
# Fresh672 right-trim study: same state and decimal1, no inference head.
# Independent execution namespace; original producer files and defaults remain unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bjWb_trim_state_digits_positive_"$stamp" --note 'Fresh672 right-trim study: same state and decimal1, no inference head.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bjWb_trim_state_digits_positive_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_trim.py --mode train --arm digits1 --execute --max-wall-sec 3600
