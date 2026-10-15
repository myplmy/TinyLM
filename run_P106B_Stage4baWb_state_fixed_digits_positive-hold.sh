#!/usr/bin/env bash
# Same672/state/native, only decimal objective1. Original inference without auxiliary head.
# Independent outputs. No stdin, implicit resume, source overwrite or inference answer selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4baWb_state_fixed_digits_positive_"$stamp" --note 'Same672/state/native, only decimal objective1. Original inference without auxiliary head.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4baWb_state_fixed_digits_positive_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_decimal.py --mode train --arm digits1 --execute --max-wall-sec 3600
