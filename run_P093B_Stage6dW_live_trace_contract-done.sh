#!/usr/bin/env bash
# CPU native observer hooks/IDs/KV/frozen shards. No private tokenizer, checkpoint or GPU load.
# Estimated 0.02h; GPU=N; cap=600 seconds. No stdin/download/cleanup.
# New stage: saved hidden snapshots did not observe actual generation onset.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage6dW_live_trace_contract_$run_stamp.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6dW_live_trace_contract_"$run_stamp" --num 103 --note 'CPU native observer hooks/IDs/KV/frozen shards. No private tokenizer, checkpoint or GPU load.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6dW_live_trace_contract_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_live_trace.py --mode contract --tag p093b_live_trace_v1_s1337 --max-wall-sec 600 --execute
