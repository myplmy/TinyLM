#!/usr/bin/env bash
# Stage1c built a valid filtered cache but aborted while background streaming
# resources finalized. Reuse the completed cache after explicit iterator close.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage1cB_edu_v2_300M \
  --note "P097 Stage1cB: reuse the completed filtered education cache after explicit stream-close and WSL native PATH fixes" || exit $?
"$python_bin" scripts/runlog.py --num 090 --name P097_Stage1cB_edu_v2_300M -- \
  /usr/bin/bash scripts/shell/run_p097_dataset_arm.sh ko-en-edu-v2 1 || exit $?
exec "$python_bin" scripts/runlog.py --num 090 --name P097_Stage1cB_edu_v2_300M -- \
  "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en-edu-v2 \
  --tokens 300M --pool-tokens 600M --exact-cache --doc-filter --doc-min-chars 50000 \
  --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd \
  --anneal-end 0.60 --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms \
  --muon-lr-mult 4 --cla-group 2 --no-ckpt --compile --seed 1337 --tag p097_edu_v2
