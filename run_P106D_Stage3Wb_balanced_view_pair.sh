#!/usr/bin/env bash
# New stage after20261010 original negative/technical completion; old namespace preserved.
# CPU compare both128update reports/actual exposure/firstanswers/native CE. Technical completion is not context reasoning or general intelligence PASS.
# Estimated 0.02h, GPU=N. Exit8 negative/HOLD,9 error,130 interruption. No stdin/download.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P106D_Stage3Wb_balanced_view_pair_${run_stamp}"
log="test_result/104_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage3Wb_balanced_view_pair_"$run_stamp" --num 104 --note 'CPU compare both128update reports/actual exposure/firstanswers/native CE. Technical completion is not context reasoning or general intelligence PASS.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage3Wb_balanced_view_pair_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_views.py --mode readback --tag p106d_ruleviews_v2_4096_s1337 --samples 4096 --execute --max-wall-sec 600
