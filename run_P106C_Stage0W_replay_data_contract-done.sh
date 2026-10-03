#!/usr/bin/env bash
# P106C_Stage0W_replay_data_contract: expected 0.05h upper scheduling estimate; phases share a four-hour cap.
# CPU code-gold data and matched token/role contracts; no model or teacher.
# No interactive input. Preserve previous/partial outputs and require a new version for retries.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/102_log_$(date +%Y%m%d)_P106C_Stage0W_replay_data_contract.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106C_Stage0W_replay_data_contract --num 102 --note 'CPU code-gold data and matched token/role contracts; no model or teacher.'
"$python_bin" scripts/runlog.py --name P106C_Stage0W_replay_data_contract --num 102 -- "$python_bin" -B -X utf8 scripts/test_p106c_replay.py
"$python_bin" scripts/runlog.py --name P106C_Stage0W_replay_data_contract --num 102 -- "$python_bin" -B -X utf8 scripts/p106c_replay.py --mode prepare --max-wall-sec 14400 --check-only
"$python_bin" scripts/runlog.py --name P106C_Stage0W_replay_data_contract --num 102 -- "$python_bin" -B -X utf8 scripts/p106c_replay.py --mode prepare --max-wall-sec 14400 --execute
