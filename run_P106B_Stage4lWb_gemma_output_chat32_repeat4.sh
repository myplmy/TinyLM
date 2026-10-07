#!/usr/bin/env bash
# User GPU estimated6-12h; matching75M/wire required. Original chat32 parent/micro8 accum16 checkpointON/LR1e-4 Muon4e-4/four actualepochs about300M nonpadding. New outputv2 tag; no teacher co-residency; quality unproven.
# User-run only; no stdin/download. Existing raw/HF/checkpoints are preserved.
# Exit8 prerequisite/negative,9 tool error; final receipt separates NOT_RUN.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4lWb_gemma_output_chat32_repeat4"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4lWb_gemma_output_chat32_repeat4 --num 101 --note 'User GPU estimated6-12h; matching75M/wire required. Original chat32 parent/micro8 accum16 checkpointON/LR1e-4 Muon4e-4/four actualepochs about300M nonpadding. New outputv2 tag; no teacher co-residency; quality unproven.'
"$python_bin" scripts/runlog.py --name P106B_Stage4lWb_gemma_output_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_output_recovery.py --mode train --execute
