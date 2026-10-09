#!/usr/bin/env bash
# User GPU only. First4 native MLP group, actual activations, rank8/16 residual function calibration. Same parent/source; no full SFT or deploy claim.
# User-owned execution. No input/pause/download. Exit8 gate,9 tool error,130 interrupt.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P093B_Stage1Wa_activation_residual_${run_stamp}"
log="test_result/103_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage1Wa_activation_residual_"$run_stamp" --num 103 --note 'User GPU only. First4 native MLP group, actual activations, rank8/16 residual function calibration. Same parent/source; no full SFT or deploy claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage1Wa_activation_residual_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_native_repair.py --mode calibrate_a --execute --max-wall-sec 3600
