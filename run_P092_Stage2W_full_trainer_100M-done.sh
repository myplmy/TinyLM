#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
failures=0
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage2W_full_trainer_100M -- \
  "$python_bin" run100m.py train --preset m100s10 --arch dense --data ko-en --tokens 300M \
    --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
    --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 --seed 1337 \
    --eval-every 100 --save-every 500 --compile --no-ckpt --optimizer muon --muon-scale rms \
    --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --connectivity-mode none \
    --connectivity-density 1.0 --connectivity-update-every 100 \
    --connectivity-swap-fraction 0.1 --tag p092_s2_dense100 \
  || { printf '%s\n' '[WARN] P092 Stage2 dense failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage2W_full_trainer_100M -- \
  "$python_bin" run100m.py train --preset m100s10 --arch dense --data ko-en --tokens 300M \
    --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
    --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 --seed 1337 \
    --eval-every 100 --save-every 500 --compile --no-ckpt --optimizer muon --muon-scale rms \
    --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --connectivity-mode static \
    --connectivity-density 0.5 --connectivity-update-every 100 \
    --connectivity-swap-fraction 0.1 --tag p092_s2_static50 \
  || { printf '%s\n' '[WARN] P092 Stage2 static50 failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage2W_full_trainer_100M -- \
  "$python_bin" run100m.py train --preset m100s10 --arch dense --data ko-en --tokens 300M \
    --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
    --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 --seed 1337 \
    --eval-every 100 --save-every 500 --compile --no-ckpt --optimizer muon --muon-scale rms \
    --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --connectivity-mode dynamic \
    --connectivity-density 0.5 --connectivity-update-every 100 \
    --connectivity-swap-fraction 0.1 --tag p092_s2_dynamic50 \
  || { printf '%s\n' '[WARN] P092 Stage2 dynamic50 failed' >&2; failures=$((failures + 1)); }
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage2W_full_trainer_100M -- \
  "$python_bin" run100m.py train --preset m100s10 --arch dense --data ko-en --tokens 300M \
    --pool-tokens 600M --exact-cache --steps 763 --micro-bs 8 --accum 16 --seq 1024 \
    --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 --seed 1337 \
    --eval-every 100 --save-every 500 --compile --no-ckpt --optimizer muon --muon-scale rms \
    --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --connectivity-mode dynamic \
    --connectivity-density 0.25 --connectivity-update-every 100 \
    --connectivity-swap-fraction 0.1 --tag p092_s2_dynamic25 \
  || { printf '%s\n' '[WARN] P092 Stage2 dynamic25 failed' >&2; failures=$((failures + 1)); }
exit "$failures"
