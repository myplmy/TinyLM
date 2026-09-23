#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" scripts/runlog.py --num 090 --name P097_Stage3bW_fineweb2_s2024 -- \
  "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en-fw2 \
    --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 \
    --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --eval-every 100 --save-every 500 \
    --optimizer muon --muon-scale rms --muon-lr-mult 4 --matrix-weight-decay 0 \
    --cla-group 2 --no-ckpt --compile --seed 2024 --tag p097_fw2_s2024
