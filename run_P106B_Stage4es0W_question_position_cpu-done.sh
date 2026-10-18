#!/usr/bin/env bash
# Completed Oct19 06:19:38 KST; source/tokenizer CPU freeze, no model or GPU.
# CQ/QC/QCQ/CQQ; same full context, no candidate or crop; no training/checkpoint writes.
# CPU and GPU authority ends Oct20 17:00 KST; main experiment never waits for stdin.
# Source/code/weights preserved; compare actual first answers and CQ reproduction, not IDs only.
# One stage uses REGRESSION/PREFLIGHT/EXECUTE and preserves HOLD8, ERROR9 and interrupt130.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export CUDA_VISIBLE_DEVICES=""
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4es0W_question_position_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4es0W_question_position_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_question_position.py --mode prepare --max-wall-sec 300 --execute
