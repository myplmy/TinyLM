#!/usr/bin/env bash
# P106C_Stage1W_replay_cost_calibration: expected 1h upper scheduling estimate; phases share a four-hour cap.
# User GPU: 40 updates and A/A replay; estimate the cumulative four-hour budget before proceeding.
# No interactive input. Preserve previous/partial outputs and require a new version for retries.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage1W_replay_cost_calibration.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage1W_replay_cost_calibration --num 102 --note 'User GPU: 40 updates and A/A replay; estimate the cumulative four-hour budget before proceeding.'
"$python_bin" scripts/runlog.py --name P106C_Stage1W_replay_cost_calibration --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_replay.py
"$python_bin" scripts/runlog.py --name P106C_Stage1W_replay_cost_calibration --num 102 -- "$python_bin" -B -X utf8 scripts/p106c_replay.py --mode calibrate --max-wall-sec 14400 --check-only
"$python_bin" scripts/runlog.py --name P106C_Stage1W_replay_cost_calibration --num 102 -- "$python_bin" -B -X utf8 scripts/p106c_replay.py --mode calibrate --max-wall-sec 14400 --execute
