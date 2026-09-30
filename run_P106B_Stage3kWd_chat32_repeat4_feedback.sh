#!/usr/bin/env bash
# P106B_Stage3kWd_chat32_repeat4_feedback: user-run only, expected 0.75h. Exit8 gate/HOLD,9 tool,130 interrupt.
# Hard2h for model gates. Scientific results cannot be inferred from CPU tests.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3kWd_chat32_repeat4_feedback.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3kWd_chat32_repeat4_feedback --num 101 --note \
  'Conditional B14 chat32 own exact parent, same full corrected corpus as A. Four passes micro8 accum16 cap checkpointON compile MuonRMS4 LR0.0001, new feedback child. Save first/within3 answers and own-native val before/after. No tokenizer-only quality claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage3kWd_chat32_repeat4_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3kWd_chat32_repeat4_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3kWd_chat32_repeat4_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3kWd_chat32_repeat4_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode train-b
"$python_bin" scripts/runlog.py --name P106B_Stage3kWd_chat32_repeat4_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode train-b
