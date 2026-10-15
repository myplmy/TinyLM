#!/usr/bin/env bash
# CPU decimal/state contracts, callback restoration, zero digit gradient and deadline arithmetic.
# Independent outputs. No stdin, implicit resume, source overwrite or inference answer selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4az0Wc_joint_final_cpu_"$stamp" --note 'CPU decimal/state contracts, callback restoration, zero digit gradient and deadline arithmetic.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4az0Wc_joint_final_cpu_"$stamp" -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_joint_decimal scripts.test_p106b_joint_decimal_driver scripts.test_p106b_state_update_aux scripts.test_p106b_state_update_driver
