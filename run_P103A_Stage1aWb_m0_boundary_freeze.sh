#!/usr/bin/env bash
# P103A Stage1aWb: rerun pinned M0 12/4 boundary after lower MLP freeze.
# About 0.4 h CPU and several GiB host RAM. Run only after Stage0dWb PASS.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage1aWb_m0_boundary_freeze --note "Pinned M0 SHA, CLA2 12/4 exact frozen lower/tail with referenced MLP frozen. Original Stage1aW gradient-presence failure retained. Same 5e-5 threshold; 2M cache/GPU/quality NOT_RUN."
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage1aWb_m0_boundary_freeze -- "$python_bin" -B -X utf8 scripts/diag_p103a_m0_boundary.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P103A corrected M0 boundary gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P103A corrected M0 CPU boundary gate; large cache/quality NOT_RUN"
