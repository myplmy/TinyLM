#!/usr/bin/env bash
# GATED three endpoints; expected1638 versus generated/not-run; no automatic adoption
# Active workers total5400sec, absolute Oct20 17:00 KST; no stdin waits.
# Same immutable old parent/fixed/views; no learning, optimizer or checkpoint writes.
# Read actual questions/answers/stops; format preservation is not factual truth.
# Three-phase receipt separates COMPLETE/HOLD8/ERROR9/interrupt130 and preserves raw.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export CUDA_VISIBLE_DEVICES=""
run_stamp="$(date +%H%M%S)"
log="test_result/104_log_$(date +%Y%m%d)_P106D_Stage5Wd_history_scope_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage5Wd_history_scope_readback_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_history_scope.py --mode readback --max-wall-sec 600 --execute
