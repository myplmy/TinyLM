#!/usr/bin/env bash
# P103A Stage0W: X1 toy prefix, X2 physical FFN tiles, X3 INT8 cache math.
# About 0.1 h CPU; no model, GPU, or 20 GB allocation.
set -u -o pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0W_compute_math_contract --note "X1 toy VJP, X2 tile output, X3 INT8 16.32GB arithmetic. Actual Transformer/RAM/quality NOT_RUN."
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0W_compute_math_contract -- "$python_bin" -B -X utf8 scripts/diag_p103a_contract.py
