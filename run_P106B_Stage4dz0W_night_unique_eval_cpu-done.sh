#!/usr/bin/env bash
# Completed once; archive exact commands and source before cleanup.
# Same immutable scientific inputs; unique32k once versus8k four-pass baseline.
# No stdin, training, checkpoint writes, installs or downloads;09:00 GPU stop.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dz0W_night_unique_eval_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dz0W_night_unique_eval_cpu_"$run_stamp" --num 101 --note 'CPU4 and same original scientific cases bound to unique32k final and DEV; no model load; repeated development cohort, no broad intelligence certificate.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dz0W_night_unique_eval_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_diversity_eval
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dz0W_night_unique_eval_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_diversity_eval.py --mode freeze --max-wall-sec 7200 --execute
