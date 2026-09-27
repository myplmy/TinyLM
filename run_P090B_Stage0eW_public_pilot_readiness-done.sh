#!/usr/bin/env bash
# P090B Stage0eW: CPU-only public-v3 + exact authorized BasicKorean pilot audit.
# No download, GPU/model, training, source rewrite, or protected held-out scan.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
"$python_bin" scripts/runlog.py --name P090B_Stage0eW_public_pilot_readiness --num 096 --note \
  'Read-only public-v3 and exact BasicKorean pilot evidence. Technical PASS is not TRAIN_READY.'
"$python_bin" scripts/runlog.py --name P090B_Stage0eW_public_pilot_readiness --num 096 -- \
  "$python_bin" -B -X utf8 scripts/diag_p090b_public_pilot_readiness.py --self-test
"$python_bin" scripts/runlog.py --name P090B_Stage0eW_public_pilot_readiness --num 096 -- \
  "$python_bin" -B -X utf8 scripts/diag_p090b_public_pilot_readiness.py \
  /mnt/z/TinyDataset/TinyDataset/BasicKorean/v1/pilot
