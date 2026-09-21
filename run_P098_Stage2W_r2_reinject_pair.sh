#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --name P098_Stage2W_r2_reinject_pair -- \
  "$python_bin" scripts/paired_eval.py --preset m100s8 --data ko-en \
    --tokens 600M --ckpt-tokens 300M --match-train-repeat \
    --models p098_r2_ctrl_s1337 p098_r2_reinject_s1337 \
    --dump-crops runs/logs/p098_reinject_s1337.json || exit $?
"$python_bin" scripts/runlog.py --name P098_Stage2W_r2_reinject_pair -- \
  "$python_bin" scripts/paired_eval.py --preset m100s8 --data ko-en \
    --tokens 600M --ckpt-tokens 300M --match-train-repeat \
    --models p098_r2_ctrl_s2024 p098_r2_reinject_s2024 \
    --dump-crops runs/logs/p098_reinject_s2024.json || exit $?
exec "$python_bin" scripts/runlog.py --name P098_Stage2W_r2_reinject_pair -- \
  "$python_bin" scripts/paired_eval.py --preset m100s8 --data ko-en \
    --tokens 600M --ckpt-tokens 300M --match-train-repeat \
    --models p098_r2_ctrl_s31415 p098_r2_reinject_s31415 \
    --dump-crops runs/logs/p098_reinject_s31415.json
