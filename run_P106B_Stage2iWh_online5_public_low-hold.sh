#!/usr/bin/env bash
# HOLD 2026-09-30 by user: retain low5 study, but disable direct launch and queue membership.
# Full teacher + P076 micro8*accum16/ckpt-on, up to 6h, no saved checkpoint.
set -euo pipefail
printf '[HOLD] Stage2iWh is preserved but not runnable until a separate decision.\n' >&2
exit 8
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2iWh_online5_public_low.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; use a new stage for a new run.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2iWh_online5_public_low --num 101 --note \
  'Requires Stage2iWg low ONE_UPDATE_COMPLETE/128 actual trained conversations, same source/parent/teacher SHA and healthy VRAM telemetry before GPU. New v18 raw/canonical write-once <=20MB shards, fresh 640 answers/5 optimizer, 6h cap; no checkpoint/held-out quality/300M claim. Independent restart from same parent, not 6 continuous updates. Medium remains HOLD; exit8 is gate negative, exit9 tool error, exit130 user interrupt.'
"$python_bin" scripts/runlog.py --name P106B_Stage2iWh_online5_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_online_lifecycle.py
"$python_bin" scripts/runlog.py --name P106B_Stage2iWh_online5_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2iWh_online5_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --check-only --effort low --variant publiclow5
"$python_bin" scripts/runlog.py --name P106B_Stage2iWh_online5_public_low --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_online_rate5.py --execute --effort low --variant publiclow5 --max-wall-sec 21600
