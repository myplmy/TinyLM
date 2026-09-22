#!/usr/bin/env bash
# P060B Stage2W: opt-in GQA on real prefill and KV-cache decode.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
ckpt="runs/ckpt/m100s10_ko-en_300M_d14_cla2_norecur_rms4.pt"

exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage2W_gqa_deploy_cache -- \
  "$python_bin" scripts/diag_sdpa_gqa_deploy.py \
    --ckpt "$ckpt" --arch dense --data ko-en --seqs 128,512,1024 \
    --max-new 32 --warmup 2 --iters 5 --max-nrms 0.001 \
    --min-cosine 0.999999 --max-slowdown 1.05 --min-benefit 0.05
