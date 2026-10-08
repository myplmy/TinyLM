#!/usr/bin/env bash
# User GPU6-12h estimate. Same successfulwire/corpusV4, originalparent/micro8 accum16 checkpointON/currentLR/four actualepochs about300M. Fresh literalv3 tag. This path is sequential, not new online feedback training.
# User-run only; no stdin/download. Exit8 prerequisite/negative,9 tool error.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4lWc_literal_chat32_repeat4"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4lWc_literal_chat32_repeat4 --num 101 --note 'User GPU6-12h estimate. Same successfulwire/corpusV4, originalparent/micro8 accum16 checkpointON/currentLR/four actualepochs about300M. Fresh literalv3 tag. This path is sequential, not new online feedback training.'
"$python_bin" scripts/runlog.py --name P106B_Stage4lWc_literal_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode train --execute
