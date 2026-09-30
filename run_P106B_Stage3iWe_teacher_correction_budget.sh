#!/usr/bin/env bash
# P106B_Stage3iWe_teacher_correction_budget: user-run only. Expected 3h, hard <=6h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iWe_teacher_correction_budget.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iWe_teacher_correction_budget --num 101 --note \
  'Conditional full96 teacher correction after observed new four-profile budget gate. Same source/low sampler/output6144 context8192, new v31/correction. Record actual length causes and raw retry responses. Existing pilot request cost extrapolates to2.795h for96 groups, not a forecast of new success. Expected3h hard6h; student training0.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iWe_teacher_correction_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWe_teacher_correction_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWe_teacher_correction_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct
"$python_bin" scripts/runlog.py --name P106B_Stage3iWe_teacher_correction_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct
