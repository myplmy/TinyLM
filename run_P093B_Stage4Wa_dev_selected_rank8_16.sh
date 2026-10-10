#!/usr/bin/env bash
# New stage after20261010 original negative/technical completion; old namespace preserved.
# User GPU only; fresh train/dev/test 2048/512/512, rank8/16, LR1e-3/1e-4, dev-selected0/20/50/100/250. Preserve actual parent/shared/corrected8 answers even when local gate is negative.
# Estimated 0.50h, GPU=Y. Exit8 negative/HOLD,9 error,130 interruption. No stdin/download.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P093B_Stage4Wa_dev_selected_rank8_16_${run_stamp}"
log="test_result/103_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage4Wa_dev_selected_rank8_16_"$run_stamp" --num 103 --note 'User GPU only; fresh train/dev/test 2048/512/512, rank8/16, LR1e-3/1e-4, dev-selected0/20/50/100/250. Preserve actual parent/shared/corrected8 answers even when local gate is negative.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage4Wa_dev_selected_rank8_16_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_calibration_recovery.py --mode tune_a --tag p093b_recovery_v2_s1337 --execute --max-wall-sec 3600
