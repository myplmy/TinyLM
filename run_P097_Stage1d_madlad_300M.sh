#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --name P097_Stage1d_madlad_300M \
  --note "P097 arm C: MADLAD clean Korean plus English, exact token 50:50, source-stratified val; 300M draw from 600M pool" || exit $?
"$python_bin" scripts/runlog.py --name P097_Stage1d_madlad_300M -- \
  /usr/bin/bash scripts/shell/run_p097_dataset_arm.sh ko-en-madlad 0 || exit $?
exec "$python_bin" scripts/runlog.py --name P097_Stage1d_madlad_300M -- \
  "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en-madlad \
  --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 \
  --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --eval-every 100 --save-every 500 \
  --optimizer muon --muon-scale rms --muon-lr-mult 4 --cla-group 2 --no-ckpt --compile \
  --seed 1337 --tag p097_madlad
