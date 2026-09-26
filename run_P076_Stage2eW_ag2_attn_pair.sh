#!/usr/bin/env bash
# P076 B3 deterministic paired full-val of the two new ag2 seed1337 checkpoints.
# User-run GPU evaluation about 0.3 h, only after both training arms succeeded.
# Same crop is a within-seed comparison, not multi-seed adoption evidence.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
for tag in p076_b3_ag2_mean_s1337 p076_b3_ag2_attnorm_s1337; do
  ckpt="runs/ckpt/m100R1c_ko-en_300M_tied_${tag}.pt"
  if [[ ! -f "$ckpt" || -L "$ckpt" ]]; then
    printf '[STOP] P076 paired input absent or linked: %s\n' "$ckpt" >&2
    exit 9
  fi
done
crops=runs/bench/p076_b3_ag2_attn_pair_crops.json
if [[ -e "$crops" || -L "$crops" ]]; then
  printf '[STOP] P076 write-once paired crops already exist: %s\n' "$crops" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P076_Stage2eW_ag2_attn_pair --note "Read same-crop paired full-val, train grad_max, resident and speed separately. One seed never adopts B3 as default."
"$python_bin" scripts/runlog.py --name P076_Stage2eW_ag2_attn_pair -- "$python_bin" -B -X utf8 scripts/paired_eval.py \
  --preset m100R1c --data ko-en --tokens 600M --ckpt-tokens 300M \
  --models p076_b3_ag2_mean_s1337 p076_b3_ag2_attnorm_s1337 \
  --device cuda --seq 1024 --micro-bs 8 --dump-crops "$crops"
