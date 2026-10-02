#!/usr/bin/env bash
# P106B_Stage4c0W_mixed_student_wire: expected0.5h. User GPU only, mixed partial source, exactly2 updates; not300M.
# Same micro8/accum16/checkpoint-on/LR, separate wire outputs. Teacher must be down.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4c0W_mixed_student_wire.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4c0W_mixed_student_wire --num 101 --note 'Mixed-source streaming/checkpoint/optimizer wire2 only, actual tokens not300M; teacher down, native/answers separate.'
"$python_bin" scripts/runlog.py --name P106B_Stage4c0W_mixed_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_mixed_scale.py
"$python_bin" scripts/runlog.py --name P106B_Stage4c0W_mixed_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --check-only --mode wire
"$python_bin" scripts/runlog.py --name P106B_Stage4c0W_mixed_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --execute --mode wire
