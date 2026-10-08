#!/usr/bin/env bash
# User GPU up to6h; successful new16/structure4/family64 before teacher allocation. New deficit V2 and final corpus V3. Exact remaining train/val/task/source quotas; raw/canonical20MB; incomplete PAUSED8, never model quality PASS.
# User-run only; no stdin/download. Existing raw/HF/checkpoints are preserved.
# Exit8 prerequisite/negative,9 tool error; final receipt separates NOT_RUN.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4jWc_gemma_output_deficit_production"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4jWc_gemma_output_deficit_production --num 101 --note 'User GPU up to6h; successful new16/structure4/family64 before teacher allocation. New deficit V2 and final corpus V3. Exact remaining train/val/task/source quotas; raw/canonical20MB; incomplete PAUSED8, never model quality PASS.'
"$python_bin" scripts/runlog.py --name P106B_Stage4jWc_gemma_output_deficit_production --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_output_recovery.py --mode produce --execute --max-wall-sec 21600
