#!/usr/bin/env bash
# Same new course, positive auxiliary1 cost8; finite gradient and active head.
# About0.05h GPU, no checkpoints. Both zero/positive cost gates before full arms.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al1Wb_binding_aux_positive_cost8_"$stamp" --note 'Actual positive1 cost8 checks the active auxiliary branch, not only coefficient0. Same frozen inputs/parent; no CPT or quality verdict.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al1Wb_binding_aux_positive_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode cost --arm aux100 --execute --max-wall-sec 600
