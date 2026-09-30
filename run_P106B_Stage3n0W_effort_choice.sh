#!/usr/bin/env bash
# P106B_Stage3n0W_effort_choice: user-run only, expected 0.1h. Exit8 gate/HOLD,9 tool,130 interrupt.
# Hard2h for model gates. Scientific results cannot be inferred from CPU tests.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
"$python_bin" scripts/runlog.py --name P106B_Stage3n0W_effort_choice --num 101 --note \
  'User operator choice after inspecting paired-panel final answers. Interactive input, only technically complete efforts eligible. No silent default, no teacher/model/GPU. Selection written once in new v32, not a scientific accuracy verdict.'
"$python_bin" scripts/runlog.py --name P106B_Stage3n0W_effort_choice --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3n0W_effort_choice --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3n0W_effort_choice --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3n0W_effort_choice --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode choose-effort
"$python_bin" scripts/runlog.py --name P106B_Stage3n0W_effort_choice --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode choose-effort
