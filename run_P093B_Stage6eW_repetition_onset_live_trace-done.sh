#!/usr/bin/env bash
# Exact old8 queries x parent/shared/r64; native greedy max96. Logits/KV/16-layer time trace and same-prefix cacheOFF. 600sec cap; no learning/checkpoint.
# Estimated 0.17h; GPU=Y; cap=600 seconds. No stdin/download/cleanup.
# New stage: saved hidden snapshots did not observe actual generation onset.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage6eW_repetition_onset_live_trace_$run_stamp.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6eW_repetition_onset_live_trace_"$run_stamp" --num 103 --note 'Exact old8 queries x parent/shared/r64; native greedy max96. Logits/KV/16-layer time trace and same-prefix cacheOFF. 600sec cap; no learning/checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6eW_repetition_onset_live_trace_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_live_trace.py --mode trace --tag p093b_live_trace_v1_s1337 --max-wall-sec 600 --execute
