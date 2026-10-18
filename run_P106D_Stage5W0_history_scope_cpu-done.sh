#!/usr/bin/env bash
# Completed 2026-10-19 07:51:38 KST; real CPU preparation, no new inference.
# CPU old64/fresh64 producer and418static128dynamic templates; three CPU tensor loads, no Module/GPU
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
log="test_result/104_log_$(date +%Y%m%d)_P106D_Stage5W0_history_scope_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106D_Stage5W0_history_scope_cpu_"$run_stamp" --num 104 -- "$python_bin" -B -X utf8 scripts/diag_p106d_history_scope.py --mode prepare --max-wall-sec 600 --execute
