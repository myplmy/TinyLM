#!/usr/bin/env bash
# CPU same-code actual causal row/shard readback. Completion is not unique repetition cause or a quality PASS.
# Estimated 0.02 h; GPU=N; hard600sec in body; no stdin/download/cleanup.
# New stage: temporal correlation alone did not distinguish cause and consequence.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage7cW_causal_readback_$run_stamp.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7cW_causal_readback_"$run_stamp" --num 103 --note 'CPU same-code actual causal row/shard readback. Completion is not unique repetition cause or a quality PASS.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage7cW_causal_readback_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_causal_probe.py --mode readback --tag p093b_causal_v1_s1337 --max-wall-sec 600 --execute
