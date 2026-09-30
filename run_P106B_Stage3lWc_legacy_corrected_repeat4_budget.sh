#!/usr/bin/env bash
# P106B_Stage3lWc_legacy_corrected_repeat4_budget: user-run only. Expected 0.75h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3lWc_legacy_corrected_repeat4_budget.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3lWc_legacy_corrected_repeat4_budget --num 101 --note \
  'Conditional A20 tied legacy own exact original parent control on same v31 corpus as B. Exact4 passes micro8 accum16 cap checkpointON compile MuonRMS4 LR0.0001. Distinct budget child/raw answers, own native-val forgetting. Independent of B training success; parents/structures/tokenizers differ.'
"$python_bin" scripts/runlog.py --name P106B_Stage3lWc_legacy_corrected_repeat4_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3lWc_legacy_corrected_repeat4_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3lWc_legacy_corrected_repeat4_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode train-a
"$python_bin" scripts/runlog.py --name P106B_Stage3lWc_legacy_corrected_repeat4_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode train-a
