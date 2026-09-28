#!/usr/bin/env bash
# P106B Stage2fWb: recover only seven missing teacher jobs after old HTTP 500.
# Old 29 attempts stay immutable; known PEG mismatch is a bounded rejected row.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage2fWb_bilingual_teacher_recovery.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] P106B Stage2fWb runlog exists: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage2fWb_bilingual_teacher_recovery --num 101 --note \
  'Old Stage2fW raw29 SHA-pinned and referenced only; retry missing cases26-32 in new ignored HF v2. Known peg-native 500 is an invalid teacher attempt, at most one new-seed retry. Unknown server errors remain exit9. Student training/checkpoint0.'
"$python_bin" scripts/runlog.py --name P106B_Stage2fWb_bilingual_teacher_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_bilingual_recovery.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage2fWb_bilingual_teacher_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_bilingual_recovery.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage2fWb_bilingual_teacher_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_bilingual_recovery.py --execute
