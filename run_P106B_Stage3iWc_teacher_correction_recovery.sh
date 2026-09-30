#!/usr/bin/env bash
# P106B_Stage3iWc_teacher_correction_recovery: user-run only. Expected 2h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iWc_teacher_correction_recovery.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iWc_teacher_correction_recovery --num 101 --note \
  'Full96 C recovery after observed four-profile pilot. Teacher one-slot low thinking sampler and same output budget; code owns canonical wrapping. Keep v29 untouched; v30 original/raw/selected/review provenance. At least75 percent groups per language and A/B context screen; this is format only, semantic truth unverified. Hard2h.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iWc_teacher_correction_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWc_teacher_correction_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWc_teacher_correction_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct
"$python_bin" scripts/runlog.py --name P106B_Stage3iWc_teacher_correction_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct
