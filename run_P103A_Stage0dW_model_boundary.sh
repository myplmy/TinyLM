#!/usr/bin/env bash
# P103A Stage0dW: frozen lower/tail fixed-window exact-cache tiny-model gate.
# About 0.1 h CPU, no corpus/GPU/large cache. User-run model loading only.
# Function failure is exit 1; INT8 numerical error is report-only at this stage.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0dW_model_boundary --note "Tiny CLA2 frozen lower/tail same-window exact cache: full-model logits/loss/all gradients/one SGD update. INT8 boundary error report only; actual M0 12/4 and 2M/20M NOT_RUN."
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0dW_model_boundary -- "$python_bin" -B -X utf8 scripts/diag_p103a_model_boundary.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P103A X3 tiny-model boundary gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P103A X3 CPU model boundary gate completed; large-cache/GPU quality NOT_RUN"
