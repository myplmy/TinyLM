#!/usr/bin/env bash
# P076 B3 Stage2eWb: Stage2eW stopped before runlog by a duplicated '_tied_' checkpoint name.
# Reuse paired_eval's resolver; keep both final checkpoints and 600M full-val conditions unchanged.
# User-run only: GPU paired evaluation about 0.3h; no training; any missing input stops before model/cache load.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
crops=runs/bench/p076_b3_ag2_attn_pair_stage2ewb_crops.json
"$python_bin" scripts/runlog.py --name P076_Stage2eWb_ag2_attn_pair --num 064 --note \
  'Stage2eW was attempted but evaluated 0 checkpoints: its launcher inserted an extra _tied_ in a tagged checkpoint name. Wb uses the shared resolver and strict write-once preflight; same two final checkpoints, 600M val, one seed, no adoption claim.'
"$python_bin" scripts/runlog.py --name P076_Stage2eWb_ag2_attn_pair --num 064 -- \
  "$python_bin" -B -X utf8 scripts/paired_eval.py \
  --preset m100R1c --data ko-en --tokens 600M --ckpt-tokens 300M \
  --models p076_b3_ag2_mean_s1337 p076_b3_ag2_attnorm_s1337 \
  --seq 1024 --micro-bs 8 --dump-crops "$crops" --check-inputs
"$python_bin" scripts/runlog.py --name P076_Stage2eWb_ag2_attn_pair --num 064 -- \
  "$python_bin" -B -X utf8 scripts/paired_eval.py \
  --preset m100R1c --data ko-en --tokens 600M --ckpt-tokens 300M \
  --models p076_b3_ag2_mean_s1337 p076_b3_ag2_attnorm_s1337 \
  --device cuda --seq 1024 --micro-bs 8 --dump-crops "$crops" --require-inputs
