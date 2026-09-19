#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
ckpt="runs/ckpt/m100s10_ko-en_300M_d14_cla2_norecur_rms4.pt"
if [[ ! -f "$ckpt" ]]; then
    printf '[STOP] required checkpoint is missing: %s\n' "$ckpt" >&2
    exit 2
fi
"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0bW_model_gqa_integration \
  --note "P060B Stage0bW: actual d14 RMS4 checkpoint, default repeat versus dispatcher enable_gqa for full forward, cache prefill/decode, speed and peak allocation; default remains off" || exit $?
exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0bW_model_gqa_integration -- \
  "$python_bin" scripts/diag_sdpa_gqa_model_path.py --ckpt "$ckpt" --arch dense \
  --seq 256 --warmup 3 --iters 10 --max-nrms 0.001 --min-cosine 0.999999
