#!/usr/bin/env bash
# P106B_Stage3hW_chat32_parent_baseline: user-run only. Expected 0.75h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3hW_chat32_parent_baseline.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing runlog preserved: %s. Use a new stage on retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3hW_chat32_parent_baseline --num 101 --note \
  'B parent baseline: exact chat32 dense14 300M checkpoint and native tokenizer/cache. Collect native full-val CE, up to4 real val-text continuations, 8 fixed bilingual questions with first attempt and up to3 attempts. No student training. Raw answers require human review; completion is technical, not intelligence PASS.'
"$python_bin" scripts/runlog.py --name P106B_Stage3hW_chat32_parent_baseline --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_generate_chat_stops.py
"$python_bin" scripts/runlog.py --name P106B_Stage3hW_chat32_parent_baseline --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3hW_chat32_parent_baseline --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3hW_chat32_parent_baseline --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode parent-b
"$python_bin" scripts/runlog.py --name P106B_Stage3hW_chat32_parent_baseline --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode parent-b
