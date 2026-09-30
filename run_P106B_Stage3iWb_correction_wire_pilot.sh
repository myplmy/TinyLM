#!/usr/bin/env bash
# P106B_Stage3iWb_correction_wire_pilot: user-run only. Expected 0.3h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iWb_correction_wire_pilot.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iWb_correction_wire_pilot --num 101 --note \
  'Four-profile C recovery: pinned observed B baseline is retained, no parent reevaluation. One/two-answer Korean/English groups, source transform teacher_repair validated before inference. Preserve raw responses even on wrapper/parser failure, original/selected/review journal in new v30. Technical wire gate only, require all profiles, at most3 attempts, no student training.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iWb_correction_wire_pilot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWb_correction_wire_pilot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWb_correction_wire_pilot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct-pilot
"$python_bin" scripts/runlog.py --name P106B_Stage3iWb_correction_wire_pilot --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct-pilot
