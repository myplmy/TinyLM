#!/usr/bin/env bash
# Approved scoped causal diagnosis600sec. Same4 cases/3 questions x parent/shared/r64; history/activation/MLP/R1-R2/precision interventions. No training/checkpoint writes.
# Estimated 0.17 h; GPU=Y; hard600sec in body; no stdin/download/cleanup.
# New stage: temporal correlation alone did not distinguish cause and consequence.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage7bW_history_mlp_layer_interventions_$run_stamp.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7bW_history_mlp_layer_interventions_"$run_stamp" --num 103 --note 'Approved scoped causal diagnosis600sec. Same4 cases/3 questions x parent/shared/r64; history/activation/MLP/R1-R2/precision interventions. No training/checkpoint writes.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7bW_history_mlp_layer_interventions_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_causal_probe.py --mode intervene --tag p093b_causal_v1_s1337 --max-wall-sec 600 --execute
