#!/usr/bin/env bash
# User GPU new108 epoch1to3 firstanswers; inherit72 parent/final with SHA; allfive native on same val. Estimate0.25h/max40min; no teacher/train/checkpoint writes.
# No stdin. Existing logs/outputs preserved; new stage for retries.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eW_saved_epoch_retention.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4eW_saved_epoch_retention --num 101 --note 'User GPU new108 epoch1to3 firstanswers; inherit72 parent/final with SHA; allfive native on same val. Estimate0.25h/max40min; no teacher/train/checkpoint writes.'
"$python_bin" scripts/runlog.py --name P106B_Stage4eW_saved_epoch_retention --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_epoch_retention.py --execute
