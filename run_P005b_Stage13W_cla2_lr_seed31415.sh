#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
failures=0
"$python_bin" scripts/runlog.py --num 078 --name P005b_Stage13W_cla2_lr_seed31415 -- \
  "$python_bin" run100m.py train --preset m100s10 --arch dense --data ko-en \
    --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 \
    --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.20 --seed 31415 \
    --eval-every 100 --save-every 500 --compile --no-ckpt --ce-chunk 2048 --init-from \
    --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
    --matrix-weight-decay 0 --tag d14_cla2_norecur_rms4_s31415 \
  || { printf '%s\n' '[WARN] P005b seed31415 lr1.0 arm failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 078 --name P005b_Stage13W_cla2_lr_seed31415 -- \
  "$python_bin" run100m.py train --preset m100s10 --arch dense --data ko-en \
    --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 \
    --seq 1024 --lr 1.5e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.20 --seed 31415 \
    --eval-every 100 --save-every 500 --compile --no-ckpt --ce-chunk 2048 --init-from \
    --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
    --matrix-weight-decay 0 --tag d14_cla2_norecur_rms4_lr15_s31415 \
  || { printf '%s\n' '[WARN] P005b seed31415 lr1.5 arm failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 078 --name P005b_Stage13W_cla2_lr_seed31415 -- \
  "$python_bin" run100m.py train --preset m100s10 --arch dense --data ko-en \
    --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 \
    --seq 1024 --lr 2e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.20 --seed 31415 \
    --eval-every 100 --save-every 500 --compile --no-ckpt --ce-chunk 2048 --init-from \
    --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 \
    --matrix-weight-decay 0 --tag d14_cla2_norecur_rms4_lr20_s31415 \
  || { printf '%s\n' '[WARN] P005b seed31415 lr2.0 arm failed' >&2; failures=$((failures + 1)); }
exit "$failures"
