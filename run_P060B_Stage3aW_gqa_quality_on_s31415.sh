#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage3aW_gqa_quality_on_s31415 -- \
  "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en \
    --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 \
    --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 \
    --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms \
    --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --sdpa-gqa --no-ckpt --compile \
    --seed 31415 --tag p060b_q_on_s31415
