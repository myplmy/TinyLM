#!/usr/bin/env bash
# User GPU no-training sameparent/shared/r64 prompt x greedy/nucleus p.95 t1. Reuse old24 greedyplain; new192 answers including24 cache-off pairs. C learning remains conditional after actual A.
# Estimated 0.25h; GPU=Y. Fresh stage, no stdin/download or automatic old-output cleanup.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage6bW_parent_shared_r64_decode_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6bW_parent_shared_r64_decode_"$run_stamp" --num 103 --note 'User GPU no-training sameparent/shared/r64 prompt x greedy/nucleus p.95 t1. Reuse old24 greedyplain; new192 answers including24 cache-off pairs. C learning remains conditional after actual A.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6bW_parent_shared_r64_decode_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_generation_attribution.py --mode decode --tag p093b_generation_v1_s1337 --execute --max-wall-sec 1800
