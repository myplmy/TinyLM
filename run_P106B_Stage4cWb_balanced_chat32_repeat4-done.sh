#!/usr/bin/env bash
# P106B_Stage4cWb_balanced_chat32_repeat4: expected 12h. Conditional balanced corpus75M and matching wire success; micro8/accum16/checkpoint-on/four passes; teacher down, new v2 outputs.
# User execution only; no interactive input. Existing logs and outputs are preserved.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cWb_balanced_chat32_repeat4.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4cWb_balanced_chat32_repeat4 --num 101 --note 'Conditional balanced corpus75M and matching wire success; micro8/accum16/checkpoint-on/four passes; teacher down, new v2 outputs.'
"$python_bin" scripts/runlog.py --name P106B_Stage4cWb_balanced_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_stage4_recovery.py
"$python_bin" scripts/runlog.py --name P106B_Stage4cWb_balanced_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --check-only --mode new-balanced
"$python_bin" scripts/runlog.py --name P106B_Stage4cWb_balanced_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_mixed_repeat4.py --execute --mode new-balanced
