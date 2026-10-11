#!/usr/bin/env bash
# User GPU explicit literalV3 continuation. Only owned budget alarm pauses8; server/OOM/persistent query failures still stop; preserve generation14 and cursor.
# Estimated 6.00h; GPU=Y. Fresh stage, no stdin/download or automatic old-output cleanup.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4jWh_budget_pause_resume_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4jWh_budget_pause_resume_"$run_stamp" --num 101 --note 'User GPU explicit literalV3 continuation. Only owned budget alarm pauses8; server/OOM/persistent query failures still stop; preserve generation14 and cursor.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4jWh_budget_pause_resume_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_budget_resume.py --mode resume --execute --max-wall-sec 21600
