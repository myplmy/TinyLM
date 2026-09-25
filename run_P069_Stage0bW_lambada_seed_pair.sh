#!/usr/bin/env bash
# P069 Stage0bW: public LAMBADA cloze, matched tied s2/s3 seed panel.
# User-run GPU benchmark, no training. Estimate 1.5 h; run alone after a fresh smoke.
# Dependent preflight/benchmark failure stops this launcher; original assets are read-only.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
output=runs/bench/p069_stage0bw_lambada_s2_s3.jsonl
name=P069_Stage0bW_lambada_seed_pair
"$python_bin" scripts/runlog.py --name P069_Stage0bW_lambada_seed_pair --note "P069 public LAMBADA 5153-row seed panel: s2/s3 differ only in seed, model/GPU user-run."
"$python_bin" scripts/runlog.py --name "$name" -- "$python_bin" -B -X utf8 scripts/diag_p069_lambada_preflight.py --self-test
"$python_bin" scripts/runlog.py --name "$name" -- "$python_bin" -B -X utf8 scripts/diag_p069_lambada_preflight.py --check-only
if [[ -e "$output" || -L "$output" ]]; then
  "$python_bin" scripts/runlog.py --name "$name" --note "STOP: item JSONL exists; a rerun needs a new stage and output basename."
  exit 9
fi
"$python_bin" scripts/runlog.py --name "$name" -- "$python_bin" -B -X utf8 scripts/eval_bench_suite.py \
  --task lambada --n 5153 --models mC_initonly_s2 mC_initonly_s3 \
  --preset m100R1c --data ko-en --model-data ko-en ko-en --model-arch tied tied \
  --tokens 300M --seq-max 1024 --seed 99 --device cuda \
  --per-item-jsonl "$output" --wandb
"$python_bin" scripts/runlog.py --name "$name" --note "Read item-level ID, strict last-word accuracy and gold CE/PPL separately. W&B is a derived view; local results stay authoritative."
