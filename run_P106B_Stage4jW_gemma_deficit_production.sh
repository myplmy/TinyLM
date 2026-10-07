#!/usr/bin/env bash
# User GPU generation up to6h; successful contract16/family64 required. New immutable production root; exact remaining KOEN/task/source quotas,3 structural attempts,20MB raw/canonical. Incomplete75M is PAUSED/HOLD8, no student.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4jW_gemma_deficit_production"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4jW_gemma_deficit_production --num 101 --note 'User GPU generation up to6h; successful contract16/family64 required. New immutable production root; exact remaining KOEN/task/source quotas,3 structural attempts,20MB raw/canonical. Incomplete75M is PAUSED/HOLD8, no student.'
"$python_bin" scripts/runlog.py --name P106B_Stage4jW_gemma_deficit_production --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_deficit_production.py --mode produce --execute --max-wall-sec 21600
