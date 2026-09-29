#!/usr/bin/env bash
# HOLD 2026-09-30 by user: retain medium5 study, but disable direct launch and queue membership.
# Requires the separate Stage2iWe one-update success with the same source SHA.
# Expected up to 6h GPU; each student target is a fresh teacher answer.
set -euo pipefail
printf '[HOLD] Stage2iWf is preserved but not runnable until a separate decision.\n' >&2
exit 8
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2iWf_online5_public_medium.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2iWf runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2iWf_online5_public_medium --num 101 --note \
  'Stage2iWe one-update PASS and same public deck SHA required before GPU. Five medium updates need 640 fresh format-ready answers from Aya Dataset/OASST2 only; exact teacher token admission and 20MB write-once raw/canonical shards. 6h wall cap; no checkpoint, formal SFT, quality or old-none causal claim. Exit8 is scientific HOLD/negative; exit9 is tool failure.'
"$python_bin" scripts/runlog.py --name P106B_Stage2iWf_online5_public_medium --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2iWf_online5_public_medium --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --check-only --effort medium --variant public5
"$python_bin" scripts/runlog.py --name P106B_Stage2iWf_online5_public_medium --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --execute --effort medium --variant public5 --max-wall-sec 21600
