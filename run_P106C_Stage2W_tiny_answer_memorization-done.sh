#!/usr/bin/env bash
# P106C_Stage2W_tiny_answer_memorization: expected 1h upper scheduling estimate; phases share a four-hour cap.
# User GPU: at most128 diagnostic memorization updates; requires successful calibration, not general intelligence.
# No interactive input. Preserve previous/partial outputs and require a new version for retries.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage2W_tiny_answer_memorization.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage2W_tiny_answer_memorization --num 102 --note 'User GPU: at most128 diagnostic memorization updates; requires successful calibration, not general intelligence.'
"$python_bin" scripts/runlog.py --name P106C_Stage2W_tiny_answer_memorization --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_replay.py
"$python_bin" scripts/runlog.py --name P106C_Stage2W_tiny_answer_memorization --num 102 -- "$python_bin" -B -X utf8 scripts/p106c_replay.py --mode overfit --max-wall-sec 14400 --check-only
"$python_bin" scripts/runlog.py --name P106C_Stage2W_tiny_answer_memorization --num 102 -- "$python_bin" -B -X utf8 scripts/p106c_replay.py --mode overfit --max-wall-sec 14400 --execute
