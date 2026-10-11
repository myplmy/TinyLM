#!/usr/bin/env bash
# User GPU only after complete same V4 corpus and teacher down. Originalparent/micro8 accum16/checkpointON two updates.
# Estimated 0.50h; GPU=Y. Fresh stage, no stdin/download or automatic old-output cleanup.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4k0We_budget_student_wire_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4k0We_budget_student_wire_"$run_stamp" --num 101 --note 'User GPU only after complete same V4 corpus and teacher down. Originalparent/micro8 accum16/checkpointON two updates.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4k0We_budget_student_wire_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode wire --execute
