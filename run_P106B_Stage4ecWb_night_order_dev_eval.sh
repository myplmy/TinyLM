#!/usr/bin/env bash
# One-time authorized overnight study; old source/models/raw read-only.
# No stdin/downloads/default changes;09:00 GPU stop/10:00 authority end.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ecWb_night_order_dev_eval_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ecWb_night_order_dev_eval_"$run_stamp" --num 101 --note 'Separate same oldDEV-CE selected representative; no TEST choice or extra learning seed; actual/annotation metrics, not broad intelligence or official harness equivalence.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ecWb_night_order_dev_eval_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_order_eval.py --mode evaluate --endpoint question_first_best --max-wall-sec 7200 --execute
