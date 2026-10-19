#!/usr/bin/env bash
# User GPU after new complete child; preserve actual72 firstanswers/multiturn/native loss; not quality PASS by collection.
# Estimated 0.50h; GPU=Y. Fresh stage, no stdin/download or automatic old-output cleanup.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4mWd_budget_literal_multiaxis_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4mWd_budget_literal_multiaxis_"$run_stamp" --num 101 --note 'User GPU after new complete child; preserve actual72 firstanswers/multiturn/native loss; not quality PASS by collection.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4mWd_budget_literal_multiaxis_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode eval --execute
