#!/usr/bin/env bash
# User GPU20-60min/max60min. NewV3 contract16 complete plus pinned priorV2 complex4/runtime/shards. Real-source family cap8/KOEN32/profile coverage; strict64, no semantic PASS. Measure actualx/wall/rejections.
# User-run only; no stdin/download. Exit8 prerequisite/negative,9 tool error.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4iWj_literal_family64"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iWj_literal_family64 --num 101 --note 'User GPU20-60min/max60min. NewV3 contract16 complete plus pinned priorV2 complex4/runtime/shards. Real-source family cap8/KOEN32/profile coverage; strict64, no semantic PASS. Measure actualx/wall/rejections.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iWj_literal_family64 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode family64 --execute
