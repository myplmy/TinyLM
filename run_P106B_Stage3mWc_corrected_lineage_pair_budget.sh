#!/usr/bin/env bash
# P106B_Stage3mWc_corrected_lineage_pair_budget: user-run only. Expected 0.1h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3mWc_corrected_lineage_pair_budget.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3mWc_corrected_lineage_pair_budget --num 101 --note \
  'Conditional exact v31 A/B reports, child/common corpus/answer hashes. First attempt and within3 remain separate. Own-native-val deltas only, no cross-tokenizer CE ranking. No GPU/model; actual answers and teacher semantic defects require later interpretation.'
"$python_bin" scripts/runlog.py --name P106B_Stage3mWc_corrected_lineage_pair_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3mWc_corrected_lineage_pair_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3mWc_corrected_lineage_pair_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode compare
"$python_bin" scripts/runlog.py --name P106B_Stage3mWc_corrected_lineage_pair_budget --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode compare
