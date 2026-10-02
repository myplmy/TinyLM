#!/usr/bin/env bash
# P106B_Stage4bW_distinct_concept_batch: expected 1.50h. Teacher-only xhigh one-server 1/2/4 distinct-concept QA in order1,2,4,4,2,1; shared3 technical retries, context32768/output16384/thinking8192; no student learning or truth gate.
# User execution only; no interactive input. New write-once output version.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bW_distinct_concept_batch.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4bW_distinct_concept_batch --num 101 --note 'Teacher-only xhigh one-server 1/2/4 distinct-concept QA in order1,2,4,4,2,1; shared3 technical retries, context32768/output16384/thinking8192; no student learning or truth gate.'
"$python_bin" scripts/runlog.py --name P106B_Stage4bW_distinct_concept_batch --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_mixed_scale.py
"$python_bin" scripts/runlog.py --name P106B_Stage4bW_distinct_concept_batch --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_concept_batch.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage4bW_distinct_concept_batch --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_concept_batch.py --execute
