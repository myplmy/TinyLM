#!/usr/bin/env bash
# User GPU only; 8 fresh updates, no checkpoint, actual cost before training.
# Estimated 0.25h; same m8 accum16 seq1024 checkpointON compiledefault when learning.
# Prediction: row ranking may improve, but free-answer/general-quality benefit is NOT established.
# Frozen originals preserved; no stdin, downloads, automatic cleanup or old overwrite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4enWa_relation_ce_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4enWa_relation_ce_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_relation_bind_entry.py --mode cost_ce --execute
