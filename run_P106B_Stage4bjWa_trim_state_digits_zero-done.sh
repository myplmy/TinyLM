#!/usr/bin/env bash
# Fresh672 right-trim study: state fixed, decimal0, same selected parent/source/native1.
# Independent execution namespace; original producer files and defaults remain unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bjWa_trim_state_digits_zero_"$stamp" --note 'Fresh672 right-trim study: state fixed, decimal0, same selected parent/source/native1.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bjWa_trim_state_digits_zero_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_trim.py --mode train --arm digits0 --execute --max-wall-sec 3600
