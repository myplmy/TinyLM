#!/usr/bin/env bash
# P106B_Stage3iW_teacher_correction: user-run only. Expected 2h, hard <=2h.
# Exit0 technical completion,8 negative/HOLD,9 tool failure,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iW_teacher_correction.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing runlog preserved: %s. Use a new stage on retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iW_teacher_correction --num 101 --note \
  'C correction: require B baseline artifact. Revisit v28 original question groups with pinned one-slot Bonsai thinking sampler, at most3 attempts. Code wraps tagged content; preserve original v28, raw attempts, correction-of IDs and selected candidates. Require at least75 percent groups per language and both tokenizer length contracts; pseudo labels remain unverified. Hard2h; no student training.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iW_teacher_correction --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_generate_chat_stops.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iW_teacher_correction --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3iW_teacher_correction --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_education_followup.py
"$python_bin" scripts/runlog.py --name P106B_Stage3iW_teacher_correction --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct
"$python_bin" scripts/runlog.py --name P106B_Stage3iW_teacher_correction --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct
