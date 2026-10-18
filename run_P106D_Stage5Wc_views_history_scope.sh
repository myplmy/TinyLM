#!/usr/bin/env bash
# GATED CPU; old views128 student546cases, C1 state versus C3 string
# Active workers total5400sec, absolute Oct20 17:00 KST; no stdin waits.
# Same immutable old parent/fixed/views; no learning, optimizer or checkpoint writes.
# Read actual questions/answers/stops; format preservation is not factual truth.
# Three-phase receipt separates COMPLETE/HOLD8/ERROR9/interrupt130 and preserves raw.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/104_log_$(date +%Y%m%d)_P106D_Stage5Wc_views_history_scope_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage5Wc_views_history_scope_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_history_scope.py --mode evaluate --endpoint views --max-wall-sec 1200 --execute
