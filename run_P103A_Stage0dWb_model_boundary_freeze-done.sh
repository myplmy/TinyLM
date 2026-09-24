#!/usr/bin/env bash
# P103A Stage0dWb: rerun tiny frozen boundary after lower MLP ownership fix.
# About 0.1 h CPU. Same 5e-5 limit and fixed windows as failed Stage0dW.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0dWb_model_boundary_freeze --note "Rerun frozen lower/tail CLA2 tiny model with referenced lower MLP also frozen. Original gradient-presence failure remains historical; exact logits/loss/all gradients/update at 5e-5. Model/GPU quality NOT_RUN."
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0dWb_model_boundary_freeze -- "$python_bin" -B -X utf8 scripts/diag_p103a_model_boundary.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P103A corrected tiny boundary gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P103A corrected tiny boundary gate; actual M0/large cache NOT_RUN"
