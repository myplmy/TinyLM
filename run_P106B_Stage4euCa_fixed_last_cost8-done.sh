#!/usr/bin/env bash
# Question wording x position recovery v2; v1 scientific selection and targets stay unchanged.
# Masked wrong assistant turns remain context-only; all actual readers run before model admission.
# Original P090B parent; micro8 accum16 seq1024 checkpointON compile-default; no teacher/MTP.
# cost bounded 900s; all four cost8 receipts and an eight-hour budget gate precede training.
# Authority ends Oct20 17:00 KST; evaluation and records are reserved.
# REGRESSION/PREFLIGHT/EXECUTE; HOLD8/ERROR9/interrupt130 are not quality verdicts.
# Independent queue entries continue after a selected failure; no stdin waits.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4euCa_fixed_last_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4euCa_fixed_last_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_question_transfer.py --mode cost --arm fixed_last --max-wall-sec 900 --execute
