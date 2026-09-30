#!/usr/bin/env bash
# P106B_Stage3iWg_teacher_correction_feedback: user-run only, expected 4h. Exit8 gate/HOLD,9 tool,130 interrupt.
# Hard6h. All other dependent stages require fresh evidence.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iWg_teacher_correction_feedback.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iWg_teacher_correction_feedback --num 101 --note \
  'Conditional full96 after observed v32 wire gate and same chosen effort/source/code. Correct malformed wording in question and answers, preserve intent/numbers/uncertainty. Keep75 percent selected groups per language, real raw/review/selected provenance. Expected4h hard6h, no student.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iWg_teacher_correction_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWg_teacher_correction_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWg_teacher_correction_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWg_teacher_correction_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct
"$python_bin" scripts/runlog.py --name P106B_Stage3iWg_teacher_correction_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct
