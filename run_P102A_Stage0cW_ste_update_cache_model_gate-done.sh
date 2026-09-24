#!/usr/bin/env bash
# P102A Stage0cW: same tiny model, three micro-batches, S2 STE cache vs per-micro reference.
# About 0.1 h CPU, no corpus/GPU. User-run model loading; Codex does not run this gate.
# Function failure is exit 1, not a scientific negative exit 8.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage0cW_ste_update_cache_model_gate --note "Tiny model STE update cache vs three per-micro refreshes: same loss/all named gradients/clip/SGD update. CPU only; CUDA peak and wall NOT_RUN."
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage0cW_ste_update_cache_model_gate -- "$python_bin" -B -X utf8 scripts/diag_p102a_ste_update_cache.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P102A S2 tiny-model gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P102A S2 CPU model gate completed; GPU speed remains NOT_RUN"
