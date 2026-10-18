#!/usr/bin/env bash
# GATED CPU freeze; base32 final; same 512 inputs, expected under 20min.
# CQ/QC/QCQ/CQQ; same full context, no candidate or crop; no training/checkpoint writes.
# CPU and GPU authority ends Oct20 17:00 KST; main experiment never waits for stdin.
# Source/code/weights preserved; compare actual first answers and CQ reproduction, not IDs only.
# One stage uses REGRESSION/PREFLIGHT/EXECUTE and preserves HOLD8, ERROR9 and interrupt130.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4esWb_base32_question_position_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4esWb_base32_question_position_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_question_position.py --mode evaluate --endpoint unique32k --max-wall-sec 1200 --execute
