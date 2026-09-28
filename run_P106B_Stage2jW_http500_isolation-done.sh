#!/usr/bin/env bash
# P106B Stage2jW: authorized teacher-only four-request HTTP 500 isolation.
# Max 10 minutes, no student loading, no training, no checkpoint writes.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2jW_http500_isolation.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2jW runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2jW_http500_isolation --num 101 --note \
  'One-instruction CPU+GPU authorization only: four fixed teacher-only requests in two fresh servers, max600s. Exact v8/v10 partial SHA pinned; no student, training, checkpoint or old output write. HTTP 500 is tool failure, not gate-negative quality.'
"$python_bin" scripts/runlog.py --name P106B_Stage2jW_http500_isolation --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_http500_isolation.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2jW_http500_isolation --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_http500_isolation.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2jW_http500_isolation --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_http500_isolation.py --execute
