#!/usr/bin/env bash
# User GPU generation up to6h per resume; replay published manifests/counters/cursor,never repeat accepted source. A failed/interrupted source is consumed to avoid fresh3-try budget. Source exhaustion requires new source decision,not repetition.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
resume_stamp="$(date +%H%M%S)"
run_name="P106B_Stage4jWb_gemma_deficit_resume_${resume_stamp}"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4jWb_gemma_deficit_resume_${resume_stamp} --num 101 --note 'User GPU generation up to6h per resume; replay published manifests/counters/cursor,never repeat accepted source. A failed/interrupted source is consumed to avoid fresh3-try budget. Source exhaustion requires new source decision,not repetition.'
"$python_bin" scripts/runlog.py --name P106B_Stage4jWb_gemma_deficit_resume_${resume_stamp} --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_deficit_production.py --mode resume --execute --max-wall-sec 21600
