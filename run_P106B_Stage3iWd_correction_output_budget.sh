#!/usr/bin/env bash
# P106B_Stage3iWd_correction_output_budget: user-run only. Expected 0.5h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iWd_correction_output_budget.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iWd_correction_output_budget --num 101 --note \
  'Four-profile output-budget recovery, same source0/32/64/65 and seeds. Low temperature1 top_p0.95 top_k20 min_p0.05 presence0 repeat1. Output6144 context8192. Preserve reasoning only in raw sidecar, canonical/ChatML remain code-owned. Language75 percent threshold is unchanged; first gate only, no student training.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iWd_correction_output_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWd_correction_output_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iWd_correction_output_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct-pilot
"$python_bin" scripts/runlog.py --name P106B_Stage3iWd_correction_output_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct-pilot
