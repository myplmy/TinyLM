#!/usr/bin/env bash
# P106B_Stage4bWb_concept_batch_plain_fields: expected 1.5h. Teacher-only paired1/2/4 concepts with plain-field instructions and warning-only scaffold observations; same xhigh budgets, no student.
# User execution only; no interactive input. Existing logs and outputs are preserved.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bWb_concept_batch_plain_fields.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4bWb_concept_batch_plain_fields --num 101 --note 'Teacher-only paired1/2/4 concepts with plain-field instructions and warning-only scaffold observations; same xhigh budgets, no student.'
"$python_bin" scripts/runlog.py --name P106B_Stage4bWb_concept_batch_plain_fields --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_stage4_recovery.py
"$python_bin" scripts/runlog.py --name P106B_Stage4bWb_concept_batch_plain_fields --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_concept_batch.py --check-only --mode recovery
"$python_bin" scripts/runlog.py --name P106B_Stage4bWb_concept_batch_plain_fields --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_concept_batch.py --execute --mode recovery
