#!/usr/bin/env bash
# P101A Stage1Wb: diagnose the three approved M0 migration arms separately.
# About 0.3 h CPU and several GiB host RAM; user-run model loading only.
# Keep the original 1e-5 function threshold and the failed Stage1W log.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage1Wb_m0_arm_attribution --note "Pinned M0 SHA, independent E384/QK/MTP main-logit drift, gradients and MTP deploy contract. Old combined Stage1W failed; threshold 1e-5 unchanged. CPU model only; training/quality NOT_RUN."
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage1Wb_m0_arm_attribution -- "$python_bin" -B -X utf8 scripts/diag_p101a_m0_arm_attribution.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P101A independent M0 arm gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P101A independent-arm CPU gate completed; GPU quality NOT_RUN"
