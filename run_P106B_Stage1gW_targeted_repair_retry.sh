#!/usr/bin/env bash
# P106B Stage1gW: user-run teacher-only retry of eight reviewed v4 defects.
# Max 3 attempts per case, hard wall about 32 min, full-GPU teacher only.
# Preserve v1-v4 and every rejected v5 attempt; no student training/acceptance.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
stamp="$(date +%Y%m%d)"
log="test_result/101_log_${stamp}_P106B_Stage1gW_targeted_repair_retry.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Stage1gW runlog exists: %s; use another stage suffix.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage1gW_targeted_repair_retry --num 101 --note \
  'Prerequisites: fresh user WSL smoke PASS; idle RTX GPU; exact v1-v4 and review SHA. The eight v4 hard-reject rows only. New v5 write-once attempt journal, never modify earlier source or student checkpoint.'
"$python_bin" scripts/runlog.py --name P106B_Stage1gW_targeted_repair_retry --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_targeted_repair.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage1gW_targeted_repair_retry --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_targeted_repair.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage1gW_targeted_repair_retry --num 101 --note \
  'Gate: 8/8 first-valid responses after at most three attempts each. Validator catches named script/entity/gender/role/typo defects only. A lint PASS is not answer truth, license, PII, student training or model quality.'
"$python_bin" scripts/runlog.py --name P106B_Stage1gW_targeted_repair_retry --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_teacher_targeted_repair.py --execute
