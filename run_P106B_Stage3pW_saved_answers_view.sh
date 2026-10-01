#!/usr/bin/env bash
# P106B_Stage3pW_saved_answers_view: CPU-only, read-only frozen evidence. Expected 0.05h; GPU/model0.
# No stdin wait, source rewrite, new scores, similarity or automatic effort selection.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3pW_saved_answers_view.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3pW_saved_answers_view --num 101 --note \
  'CPU/read-only gate. No interactive input or teacher/student loading. Show actual frozen v32 source questions, all effort answers and saved parent/child attempts; recorded lexical and narrow rubric labels are not semantic truth. PASS is only this technical evidence scope.'
"$python_bin" scripts/runlog.py --name P106B_Stage3pW_saved_answers_view --num 101 -- \
  "$python_bin" -B -X utf8 scripts/view_p106b_saved_answers.py --mode panel --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3pW_saved_answers_view --num 101 -- \
  "$python_bin" -B -X utf8 scripts/view_p106b_saved_answers.py --mode education --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3pW_saved_answers_view --num 101 -- \
  "$python_bin" -B -X utf8 scripts/view_p106b_saved_answers.py --mode panel
"$python_bin" scripts/runlog.py --name P106B_Stage3pW_saved_answers_view --num 101 -- \
  "$python_bin" -B -X utf8 scripts/view_p106b_saved_answers.py --mode education
