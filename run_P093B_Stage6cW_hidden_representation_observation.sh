#!/usr/bin/env bash
# User GPU only after exact permission. Sameparent/shared/r64 saved-text48 forwards, finalhidden return without head; same-token and distinct-token cosine/rank observations. No generation/update/checkpoint.
# Estimated 0.08h; GPU=Y. Fresh stage, no stdin/download or automatic old-output cleanup.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage6cW_hidden_representation_observation_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6cW_hidden_representation_observation_"$run_stamp" --num 103 --note 'User GPU only after exact permission. Sameparent/shared/r64 saved-text48 forwards, finalhidden return without head; same-token and distinct-token cosine/rank observations. No generation/update/checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6cW_hidden_representation_observation_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_generation_attribution.py --mode representation --tag p093b_generation_v1_s1337 --execute --max-wall-sec 600
