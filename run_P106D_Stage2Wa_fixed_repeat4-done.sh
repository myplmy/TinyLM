#!/usr/bin/env bash
# User GPU only. Pinned chat32 parent, micro8 accum16 checkpointON compile-default originalLR, fixed4epoch8updates; diagnostic not300M.
# User-owned execution. No input/pause/download. Exit8 gate,9 tool error,130 interrupt.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
run_name="P106D_Stage2Wa_fixed_repeat4_${run_stamp}"
log="test_result/104_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage2Wa_fixed_repeat4_"$run_stamp" --num 104 --note 'User GPU only. Pinned chat32 parent, micro8 accum16 checkpointON compile-default originalLR, fixed4epoch8updates; diagnostic not300M.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage2Wa_fixed_repeat4_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_views.py --mode fixed --execute --max-wall-sec 1800
