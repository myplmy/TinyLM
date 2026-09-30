#!/usr/bin/env bash
# P106B_Stage3lWb_legacy_corrected_repeat4_recovery: user-run only. Expected 0.75h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3lWb_legacy_corrected_repeat4_recovery.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3lWb_legacy_corrected_repeat4_recovery --num 101 --note \
  'A20 tied legacy original P076 parent control, same v30 raw corpus/settings as B with its own tokenizer/cache. Exact4 passes, no artificial refill of short groups. Save distinct recovery child/raw answers/native-val forgetting. Architecture and pretrain parents differ, causal tokenizer effect not claimed. Hard2h.'
"$python_bin" scripts/runlog.py --name P106B_Stage3lWb_legacy_corrected_repeat4_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3lWb_legacy_corrected_repeat4_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3lWb_legacy_corrected_repeat4_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode train-a
"$python_bin" scripts/runlog.py --name P106B_Stage3lWb_legacy_corrected_repeat4_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode train-a
