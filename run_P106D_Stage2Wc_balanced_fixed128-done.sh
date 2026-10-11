#!/usr/bin/env bash
# New stage after20261010 original negative/technical completion; old namespace preserved.
# User GPU originalchat32/micro8 accum16/ckptON/LR4epochs128updates after current4096 readiness. Balanced fixed curriculum; prior64 plus fresh64 firstanswers; not300M.
# Estimated 0.50h, GPU=Y. Exit8 negative/HOLD,9 error,130 interruption. No stdin/download.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P106D_Stage2Wc_balanced_fixed128_${run_stamp}"
log="test_result/104_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage2Wc_balanced_fixed128_"$run_stamp" --num 104 --note 'User GPU originalchat32/micro8 accum16/ckptON/LR4epochs128updates after current4096 readiness. Balanced fixed curriculum; prior64 plus fresh64 firstanswers; not300M.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage2Wc_balanced_fixed128_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_views.py --mode fixed --tag p106d_ruleviews_v2_4096_s1337 --samples 4096 --execute --max-wall-sec 1800
