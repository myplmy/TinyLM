#!/usr/bin/env bash
# User CPU only after fresh contract. Same4096 canonical target; no padding/filler; real chat32 lengths and prior val exclusion.
# Estimated 0.25h; GPU=N. Fresh stage, no stdin/download or automatic old-output cleanup.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/104_log_$(date +%Y%m%d)_P106D_Stage1Wc_length_corpus4096_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage1Wc_length_corpus4096_"$run_stamp" --num 104 --note 'User CPU only after fresh contract. Same4096 canonical target; no padding/filler; real chat32 lengths and prior val exclusion.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage1Wc_length_corpus4096_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_views.py --mode prepare --tag p106d_ruleviews_v3_length_s1337 --samples 4096 --execute --max-wall-sec 3600
