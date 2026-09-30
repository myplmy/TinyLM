#!/usr/bin/env bash
# P106B_Stage3jWd_shared_corpus_feedback: user-run only, expected 0.1h. Exit8 gate/HOLD,9 tool,130 interrupt.
# Hard2h for model gates. Scientific results cannot be inferred from CPU tests.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3jWd_shared_corpus_feedback.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage/version to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3jWd_shared_corpus_feedback --num 101 --note \
  'Full correction quality gate required; pilot cannot supply this corpus. Same concept/question variants stay in one split, both tokenizer masks and actual token denominators. Exact probe overlap rejected. CPU only.'
"$python_bin" scripts/runlog.py --name P106B_Stage3jWd_shared_corpus_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3jWd_shared_corpus_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3jWd_shared_corpus_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3jWd_shared_corpus_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode prepare
"$python_bin" scripts/runlog.py --name P106B_Stage3jWd_shared_corpus_feedback --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode prepare
