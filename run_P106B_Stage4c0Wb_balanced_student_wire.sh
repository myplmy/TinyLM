#!/usr/bin/env bash
# P106B_Stage4c0Wb_balanced_student_wire: expected 0.5h. Balanced C corpus, two optimizer updates, actual row/token accounting and hash16 validation rows per language; teacher down, no300M claim.
# User execution only; no interactive input. Existing logs and outputs are preserved.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4c0Wb_balanced_student_wire.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4c0Wb_balanced_student_wire --num 101 --note 'Balanced C corpus, two optimizer updates, actual row/token accounting and hash16 validation rows per language; teacher down, no300M claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage4c0Wb_balanced_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_stage4_recovery.py
"$python_bin" scripts/runlog.py --name P106B_Stage4c0Wb_balanced_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --check-only --mode wire-balanced
"$python_bin" scripts/runlog.py --name P106B_Stage4c0Wb_balanced_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --execute --mode wire-balanced
