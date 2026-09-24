#!/usr/bin/env bash
# P101A Stage1Wc: attribute E384 FP32 input/body/head drift after Stage1Wb gate failure.
# User-run CPU M0 model, about 0.3 h and several GiB host RAM; no training/GPU.
# Diagnostic exit 0 means measurements completed, NOT that the original 1e-5 gate passed.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage1Wc_e384_roundoff_attribution --note "E384 old-block and zero-new-U, FP32 input/body/head vs FP64 math; original 1e-5 Stage1Wb gate remains FAIL. User-run CPU model, no training."
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage1Wc_e384_roundoff_attribution -- "$python_bin" -B -X utf8 scripts/diag_p101a_e384_roundoff.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P101A E384 attribution execution rc=$rc" >&2
    exit "$rc"
fi
echo "[DIAGNOSTIC COMPLETE] E384 training remains HOLD; inspect the runlog before any new plan"
