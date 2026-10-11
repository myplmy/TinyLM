#!/usr/bin/env bash
# User GPU up to6h explicit literalV3 resume. Timeout-only max3 memory queries with gap evidence; persistent errors/low free/server exit still stop. Preserve inputs and batch0/1; append new batch; unique log. No GPU-reset or quality guarantee.
# User-run only; no stdin/download. Exit8 is prerequisite/partial,9 error,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P106B_Stage4jWg_telemetry_deficit_resume_${run_stamp}"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4jWg_telemetry_deficit_resume_"$run_stamp" --num 101 --note 'User GPU up to6h explicit literalV3 resume. Timeout-only max3 memory queries with gap evidence; persistent errors/low free/server exit still stop. Preserve inputs and batch0/1; append new batch; unique log. No GPU-reset or quality guarantee.'
"$python_bin" scripts/runlog.py --name P106B_Stage4jWg_telemetry_deficit_resume_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_telemetry_resume.py --mode resume --execute --max-wall-sec 21600
