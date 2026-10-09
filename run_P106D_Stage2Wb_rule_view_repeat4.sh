#!/usr/bin/env bash
# User GPU only. Same parent/batch/LR/4epoch8updates/root/x/targets; epoch view only changes. Independent from fixed scientific outcome.
# User-owned execution. No input/pause/download. Exit8 gate,9 tool error,130 interrupt.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P106D_Stage2Wb_rule_view_repeat4_${run_stamp}"
log="test_result/104_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage2Wb_rule_view_repeat4_"$run_stamp" --num 104 --note 'User GPU only. Same parent/batch/LR/4epoch8updates/root/x/targets; epoch view only changes. Independent from fixed scientific outcome.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage2Wb_rule_view_repeat4_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_views.py --mode views --execute --max-wall-sec 1800
