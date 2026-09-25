#!/usr/bin/env bash
# P060B Stage2bW: user-run GPU model attribution of cache versus decode GQA drift.
# Same d14 dense checkpoint and gate thresholds as Stage2W; no training or cache writes.
# Estimate 0.5 h alone/watch. Exit 4 is agreement/text negative, 5 runtime failure,
# and 8 is a valid speed/memory negative. The model default remains GQA off.
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
ckpt=runs/ckpt/m100s10_ko-en_300M_d14_cla2_norecur_rms4.pt
if [[ ! -f "$ckpt" || -L "$ckpt" ]]; then
  printf '[STOP] exact regular checkpoint missing: %s\n' "$ckpt" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P060B_Stage2bW_gqa_cache_attribution --note "P060B crossed cache/decode GQA paths; user GPU diagnostic only, no training."
"$python_bin" scripts/runlog.py --name P060B_Stage2bW_gqa_cache_attribution -- "$python_bin" -B -X utf8 scripts/test_sdpa_gqa_attribution_gate.py
"$python_bin" scripts/runlog.py --name P060B_Stage2bW_gqa_cache_attribution -- "$python_bin" -B -X utf8 scripts/diag_sdpa_gqa_deploy_attribution.py \
  --ckpt "$ckpt" --arch dense --data ko-en --seqs 128,512,1023,1024 \
  --max-new 32 --warmup 2 --iters 5 --max-nrms 0.001 \
  --min-cosine 0.999999 --max-slowdown 1.05 --min-benefit 0.05
