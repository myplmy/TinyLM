#!/usr/bin/env bash
# New stage after20261010 original negative/technical completion; old namespace preserved.
# CPU inline-label/context/root/large-curriculum contracts only. --samples4096 means canonical rows; no real tokenizer/model.
# Estimated 0.02h, GPU=N. Exit8 negative/HOLD,9 error,130 interruption. No stdin/download.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P106D_Stage0bW_recovery_contract_${run_stamp}"
log="test_result/104_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage0bW_recovery_contract_"$run_stamp" --num 104 --note 'CPU inline-label/context/root/large-curriculum contracts only. --samples4096 means canonical rows; no real tokenizer/model.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage0bW_recovery_contract_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_views.py --mode contract --tag p106d_ruleviews_v2_4096_s1337 --samples 4096 --execute --max-wall-sec 600
