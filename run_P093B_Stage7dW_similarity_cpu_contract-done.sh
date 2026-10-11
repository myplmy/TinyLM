#!/usr/bin/env bash
# CPU readout-nullspace reflection algebra5 and per-channel RMS/scale controls only; no private source or model.
# Estimated 0.02h; GPU=N; hard120sec; no stdin/download/cleanup.
# New stage: full-state patching changes information as well as cosine.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage7dW_similarity_cpu_contract_$run_stamp.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7dW_similarity_cpu_contract_"$run_stamp" --num 103 --note 'CPU readout-nullspace reflection algebra5 and per-channel RMS/scale controls only; no private source or model.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7dW_similarity_cpu_contract_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_similarity_control.py --mode contract --tag p093b_similarity_control_v1_s1337 --max-wall-sec 120 --execute
