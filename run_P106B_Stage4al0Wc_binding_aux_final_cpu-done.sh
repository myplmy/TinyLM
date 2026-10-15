#!/usr/bin/env bash
# CPU13: trusted metadata, prefix causality, gradient, consumer budget/public panel.
# About0.02h CPU, no target checkpoint, teacher, GPU or existing data mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wc_binding_aux_final_cpu_"$stamp" --note 'CPU13 final contracts. Public source wrapper is software-owned, original answer unchanged; fixed stratified16 and disclosed generation cap. Does not establish CUDA/learning quality.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wc_binding_aux_final_cpu_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_binding_auxiliary.py
