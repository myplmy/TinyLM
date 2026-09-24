#!/usr/bin/env bash
# P104A Stage1W: run after Windows Stage1Bb against the same tiny dense checkpoint.
# About 0.1 h GPU. This is a functional bridge, not a full M5 quality result.
set -u -o pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
if [[ ! -f runs/bench/p104a_m5_windows.json ]]; then
    echo "[STOP] run the Windows Stage1Bb BAT first and place its JSON in this same repo" >&2
    exit 2
fi
"$python_bin" scripts/runlog.py --num 095 --name P104A_Stage1W_m5_dense_bridge --note "Compare same checkpoint/code/input SHA, eval CE and one SGD update across Windows and WSL. Do not claim full M5 quality."
"$python_bin" scripts/runlog.py --num 095 --name P104A_Stage1W_m5_dense_bridge -- "$python_bin" -B -X utf8 scripts/diag_m5_dense_bridge.py --platform wsl --out runs/bench/p104a_m5_wsl.json
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] WSL dense bridge collection failed" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 095 --name P104A_Stage1W_m5_dense_bridge -- "$python_bin" -B -X utf8 scripts/check_m5_dense_bridge.py --win runs/bench/p104a_m5_windows.json --wsl runs/bench/p104a_m5_wsl.json
