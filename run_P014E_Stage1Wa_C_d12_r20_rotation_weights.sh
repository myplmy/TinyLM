#!/usr/bin/env bash
# P014E Stage1Wa C: user-run CPU actual-weight rotation microdiagnostic.
# Read-only checkpoint, synthetic activations, 1 CPU thread; no full-model adoption.
# Estimate 0.3 h alone/watch after a fresh smoke. Other A/B/C arms are independent.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
export OPENBLAS_NUM_THREADS=1
python_bin="$(tinylm_python)"
ckpt=runs/ckpt/m100s8_ko-en_300M_d12_cla2_r20.pt
if [[ ! -f "$ckpt" || -L "$ckpt" ]]; then
  printf '[STOP] exact regular checkpoint missing: %s\n' "$ckpt" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P014E_Stage1Wa_C_d12_r20_rotation_weights --note "P014E C: same-checkpoint no-rotation/3x256/pad1024; actual weights but synthetic inputs."
"$python_bin" scripts/runlog.py --name P014E_Stage1Wa_C_d12_r20_rotation_weights -- "$python_bin" -B -X utf8 scripts/diag_p014e_checkpoint_rotation.py --self-test
"$python_bin" scripts/runlog.py --name P014E_Stage1Wa_C_d12_r20_rotation_weights -- "$python_bin" -B -X utf8 scripts/diag_p014e_checkpoint_rotation.py \
  --check-only --arch dense --ckpt "$ckpt"
"$python_bin" scripts/runlog.py --name P014E_Stage1Wa_C_d12_r20_rotation_weights -- "$python_bin" -B -X utf8 scripts/diag_p014e_checkpoint_rotation.py \
  --arch dense --ckpt "$ckpt" --seed 20260926 --batch 8 --warmup 2 --iters 7
