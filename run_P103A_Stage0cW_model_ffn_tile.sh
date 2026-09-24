#!/usr/bin/env bash
# P103A Stage0cW: physical FFN tile tiny-model function and gradient gate.
# About 0.1 h CPU, no corpus/GPU. User-run model loading; Codex does not run this gate.
# Function failure is exit 1, not a speed or quality negative.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0cW_model_ffn_tile --note "Full four-tile tiny-model loss/all gradients/SGD update vs original plus one physical 64-channel tile. Optimizer state remains full; GPU wall and quality NOT_RUN."
"$python_bin" scripts/runlog.py --num 094 --name P103A_Stage0cW_model_ffn_tile -- "$python_bin" -B -X utf8 scripts/diag_p103a_model_ffn_tile.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P103A X2 tiny-model gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P103A X2 CPU model gate completed; GPU speed remains NOT_RUN"
