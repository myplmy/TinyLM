#!/usr/bin/env bash
# P030B Stage0W: user-run CPU decode and resident-memory measurement.
# No training or GPU. Run after a fresh smoke; estimate <= 0.6 h alone.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
for tag in d14_cla2_norecur d14_cla2_norecur_rms4; do
  ckpt="runs/ckpt/m100s10_ko-en_300M_${tag}.pt"
  if [[ ! -f "$ckpt" || -L "$ckpt" ]]; then
    printf '[STOP] exact checkpoint missing or symlink: %s\n' "$ckpt" >&2
    exit 9
  fi
done
"$python_bin" scripts/runlog.py --name P030B_Stage0W_wsl_cpu_d14_rms4 --note "Same-session d14 CPU1/4 decode and physical RSS. Historical Windows Stage5 is not a same-condition speed delta."
"$python_bin" scripts/runlog.py --name P030B_Stage0W_wsl_cpu_d14_rms4 -- "$python_bin" -B -X utf8 scripts/bench_infer.py \
  --models d14_cla2_norecur d14_cla2_norecur_rms4 --preset m100s10 --data ko-en --tokens 300M \
  --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store \
  --unpack-cache --logits-last-only --check-cache --cpu-watch --cpu-baseline 10 --require-all
"$python_bin" scripts/runlog.py --name P030B_Stage0W_wsl_cpu_d14_rms4 -- "$python_bin" -B -X utf8 scripts/mem_runtime.py \
  --models d14_cla2_norecur d14_cla2_norecur_rms4 --preset m100s10 --data ko-en --tokens 300M \
  --device cpu --drop-latent --int8-store --unpack-cache --kv-seq 1024 --kv-dtype fp32 --require-all
