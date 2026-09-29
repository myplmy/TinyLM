#!/usr/bin/env bash
# P106B Stage2iWe: one public-only Aya/OASST2 online medium update.
# Technical rate/resource gate, not accepted SFT or model-quality evidence.
# Expected up to 2h GPU; fail closed on source, tokenizer, parent or teacher gate.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2iWe_online1_public_medium.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2iWe runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2iWe_online1_public_medium --num 101 --note \
  'Public Aya Dataset/OASST2 CARD_ONLY train jobs only. New medium one-update gate after OASST1 finite-pool failure; actual teacher token admission, unique concepts, micro8*accum16, full teacher, 2h wall cap. Do not compare causally with old none; no checkpoint, held-out quality or TRAIN_READY claim. Exit8 is scientific HOLD/negative; exit9 is tool failure.'
"$python_bin" scripts/runlog.py --name P106B_Stage2iWe_online1_public_medium --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2iWe_online1_public_medium --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --check-only --effort medium --variant public1
"$python_bin" scripts/runlog.py --name P106B_Stage2iWe_online1_public_medium --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --execute --effort medium --variant public1 --max-wall-sec 7200
