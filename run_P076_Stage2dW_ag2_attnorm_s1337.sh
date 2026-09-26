#!/usr/bin/env bash
# P076 B3 candidate: only shared attention parent aggregation is norm_mean.
# MLP stays mean. Same ag2 parent/pool/recipe/seed as Stage2cW control.
# User-run 300.024M tokens, about 2.7 GPU h; run only after Stage2bW contract PASS.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
parent=runs/ckpt/m100_ko-en_300M_dense.pt
cache=data_cache/ko-en_600000000
stem=m100R1c_ko-en_300M_tied_p076_b3_ag2_attnorm_s1337
if [[ ! -f "$parent" || -L "$parent" || ! -f "$cache/meta.json" || ! -f "$cache/train.bin" || ! -f "$cache/val.bin" ]]; then
  printf '%s\n' '[STOP] P076 exact parent or 600M cache missing; no build/download attempted.' >&2
  exit 9
fi
if [[ -e "runs/logs/$stem.json" || -e "runs/ckpt/$stem.pt" || -e "runs/ckpt/${stem}_best.pt" ]]; then
  printf '[STOP] P076 write-once output already exists: %s\n' "$stem" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P076_Stage2dW_ag2_attnorm_s1337 --note "P076 B3 attention-only norm_mean candidate. MLP mean and all other conditions match Stage2cW; no default adoption."
"$python_bin" scripts/runlog.py --name P076_Stage2dW_ag2_attnorm_s1337 -- "$python_bin" -B -X utf8 scripts/diag_p076_attn_only.py
"$python_bin" scripts/runlog.py --name P076_Stage2dW_ag2_attnorm_s1337 -- "$python_bin" -B -X utf8 run100m.py train \
  --arch tied --preset m100R1c --data ko-en --tokens 300M --pool-tokens 600M --exact-cache \
  --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd \
  --anneal-end 0.60 --decay-frac 0.20 --eval-every 100 --save-every 500 \
  --optimizer muon --muon-scale rms --muon-lr-mult 4 --matrix-weight-decay 0 \
  --cla-group 2 --attn-group 2 --no-ckpt --compile --ce-chunk 2048 \
  --init-from --depth-init prop --group-init mean --attn-group-init norm_mean --seed 1337 \
  --tag p076_b3_ag2_attnorm_s1337
