#!/usr/bin/env bash
# P106B_Stage3iWf_wire_content_gate: user-run only, expected 0.75h. Exit8 gate/HOLD,9 tool,130 interrupt.
# Hard2h for model gates. Scientific results cannot be inferred from CPU tests.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iWf_wire_content_gate.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iWf_wire_content_gate --num 101 --note \
  'Chosen effort from current panel,16k total/8k thinking/32k context. Four-profile technical wire requires real parser plus both tokenizer masks. Content-bad rows still rejected; pilot wire PASS does not authorize student training. Maximum3 corrective retries with exact bad text/role/position.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iWf_wire_content_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWf_wire_content_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWf_wire_content_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWf_wire_content_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct-pilot
"$python_bin" scripts/runlog.py --name P106B_Stage3iWf_wire_content_gate --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct-pilot
