#!/usr/bin/env bash
# P106B_Stage3nW_effort_upper_budget_panel: user-run only, expected 1h. Exit8 gate/HOLD,9 tool,130 interrupt.
# Hard2h for model gates. Scientific results cannot be inferred from CPU tests.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3nW_effort_upper_budget_panel.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3nW_effort_upper_budget_panel --num 101 --note \
  'Same four profiles/source/seeds/16k total output/8k numerical thinking budget/32k context; low medium xhigh crossed order,12 requests,no retries. Preserve final/reasoning sidecars. A valid low label is not calibrated short reasoning. Record wall/token and usable candidates separately, truth/student NOT_RUN.'
"$python_bin" scripts/runlog.py --name P106B_Stage3nW_effort_upper_budget_panel --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3nW_effort_upper_budget_panel --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3nW_effort_upper_budget_panel --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3nW_effort_upper_budget_panel --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode effort-panel
"$python_bin" scripts/runlog.py --name P106B_Stage3nW_effort_upper_budget_panel --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode effort-panel
