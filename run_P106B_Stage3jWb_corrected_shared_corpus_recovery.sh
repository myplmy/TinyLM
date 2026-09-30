#!/usr/bin/env bash
# P106B_Stage3jWb_corrected_shared_corpus_recovery: user-run only. Expected 0.1h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interruption.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3jWb_corrected_shared_corpus_recovery.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3jWb_corrected_shared_corpus_recovery --num 101 --note \
  'Common corrected corpus after C recovery. Same concept/normalized question stay together; exact fixed-probe overlap rejected. A/B own tokenizer lengths/masks and actual tokens recorded. New v30 prepare only, no model or GPU.'
"$python_bin" scripts/runlog.py --name P106B_Stage3jWb_corrected_shared_corpus_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3jWb_corrected_shared_corpus_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3jWb_corrected_shared_corpus_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode prepare
"$python_bin" scripts/runlog.py --name P106B_Stage3jWb_corrected_shared_corpus_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode prepare
