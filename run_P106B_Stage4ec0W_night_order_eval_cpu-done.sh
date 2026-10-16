#!/usr/bin/env bash
# Completed once; archive exact commands and source before cleanup.
# One-time authorized overnight study; old source/models/raw read-only.
# No stdin/downloads/default changes;09:00 GPU stop/10:00 authority end.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ec0W_night_order_eval_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ec0W_night_order_eval_cpu_"$run_stamp" --num 101 --note 'CPU4 same original three-format/retention/public cases binding, no model load; actual/annotation metrics, not broad intelligence or official harness equivalence.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ec0W_night_order_eval_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_order_eval
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ec0W_night_order_eval_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_order_eval.py --mode freeze --max-wall-sec 7200 --execute
