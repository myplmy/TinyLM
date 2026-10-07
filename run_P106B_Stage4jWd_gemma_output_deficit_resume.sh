#!/usr/bin/env bash
# User GPU up to6h per explicit resume. Same code/pilot/source SHA and published manifests/cursor/counters. Failed sources consumed; no renewed3-try budget or repeated filler. Unique timestamp log; no automatic loop.
# User-run only; no stdin/download. Existing raw/HF/checkpoints are preserved.
# Exit8 prerequisite/negative,9 tool error; final receipt separates NOT_RUN.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P106B_Stage4jWd_gemma_output_deficit_resume_${run_stamp}"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4jWd_gemma_output_deficit_resume_"$run_stamp" --num 101 --note 'User GPU up to6h per explicit resume. Same code/pilot/source SHA and published manifests/cursor/counters. Failed sources consumed; no renewed3-try budget or repeated filler. Unique timestamp log; no automatic loop.'
"$python_bin" scripts/runlog.py --name P106B_Stage4jWd_gemma_output_deficit_resume_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_output_recovery.py --mode resume --execute --max-wall-sec 21600
