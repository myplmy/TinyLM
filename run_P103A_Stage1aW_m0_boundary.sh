#!/usr/bin/env bash
# P103A Stage1aW: pinned actual M0 16-layer CLA2 12/4 exact frozen boundary.
# About 0.4 h CPU, several GiB host RAM. User-run model loading only; no GPU/training corpus.
# Function failure is exit 1. INT8 boundary NRMS is report-only here.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage1aW_m0_boundary --note "Pinned M0 SHA and actual 16-layer CLA2 12/4 frozen lower/tail exact fixed-window logits/loss/all gradients/SGD update. CPU model only; 2M/20M RAM and quality NOT_RUN."
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage1aW_m0_boundary -- "$python_bin" -B -X utf8 scripts/diag_p103a_m0_boundary.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P103A M0 12/4 boundary gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P103A M0 CPU exact-boundary gate completed; large-cache/GPU quality NOT_RUN"
