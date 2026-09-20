#!/usr/bin/env bash
# P076 Stage2W: mean/middle/norm_mean full-quality comparison. The Stage1W
# step0 ordering is not used as a quality prediction. User GPU training only.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
crops="runs/logs/p076_stage2_group_init_fullval.json"
if [[ -e "$crops" ]]; then
  printf '[STOP] paired output already exists: %s\n' "$crops" >&2
  exit 3
fi

"$python_bin" scripts/runlog.py --num 064 --name P076_Stage2W_group_init_quality \
  --note "P076 Stage2W: same parent and current Muon RMS4 recipe; only mean, middle, norm_mean parent aggregation changes" \
  || exit $?

failures=0
"$python_bin" scripts/runlog.py --num 064 --name P076_Stage2W_group_init_quality -- \
  "$python_bin" run100m.py train --arch tied --preset m100R1c --data ko-en \
  --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 \
  --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 \
  --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms \
  --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile \
  --ce-chunk 2048 --init-from --depth-init prop --group-init mean \
  --seed 1337 --tag p076_s2_mean
mean_rc=$?
if (( mean_rc == 0 )); then
  /usr/bin/bash scripts/shell/tool_wandb_push.sh p076_s2_mean
else
  printf '%s\n' '[WARN] P076 mean arm failed; continuing' >&2
  failures=$((failures + 1))
fi

"$python_bin" scripts/runlog.py --num 064 --name P076_Stage2W_group_init_quality -- \
  "$python_bin" run100m.py train --arch tied --preset m100R1c --data ko-en \
  --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 \
  --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 \
  --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms \
  --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile \
  --ce-chunk 2048 --init-from --depth-init prop --group-init middle \
  --seed 1337 --tag p076_s2_middle
middle_rc=$?
if (( middle_rc == 0 )); then
  /usr/bin/bash scripts/shell/tool_wandb_push.sh p076_s2_middle
else
  printf '%s\n' '[WARN] P076 middle arm failed; continuing' >&2
  failures=$((failures + 1))
fi

"$python_bin" scripts/runlog.py --num 064 --name P076_Stage2W_group_init_quality -- \
  "$python_bin" run100m.py train --arch tied --preset m100R1c --data ko-en \
  --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 \
  --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20 \
  --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms \
  --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile \
  --ce-chunk 2048 --init-from --depth-init prop --group-init norm_mean \
  --seed 1337 --tag p076_s2_normmean
norm_rc=$?
if (( norm_rc == 0 )); then
  /usr/bin/bash scripts/shell/tool_wandb_push.sh p076_s2_normmean
else
  printf '%s\n' '[WARN] P076 norm_mean arm failed; continuing' >&2
  failures=$((failures + 1))
fi

if (( failures > 0 )); then
  printf '[FAIL] P076 Stage2 training failures=%d; paired evaluation not run\n' "$failures" >&2
  exit 4
fi

exec "$python_bin" scripts/runlog.py --num 064 --name P076_Stage2W_group_init_quality -- \
  "$python_bin" scripts/paired_eval.py --preset m100R1c --data ko-en --tokens 600M \
  --ckpt-tokens 300M --models p076_s2_mean p076_s2_middle p076_s2_normmean \
  --dump-crops "$crops"
