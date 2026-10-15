#!/usr/bin/env bash
# Strict CPU-only head seeding fixes v1 CUDA RNG side effect before GPU training.
# Plan P106B Stage4bl-bn recovery: unchanged verified source, distinct execution tag.
# CPU then source contract then both cost8 then two96-update arms then raw answers.
# Micro8 accum16 ckptON, native1; no stdin/download/old writes/global queue/smoke.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bnWb_grounded_span_strict_answers_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bnWb_grounded_span_strict_answers_"$run_stamp" --num 101 --note 'Strict RNG execution v3 on immutable public source v1. Report unpadded/assistant/native counts separately; positions are not truth. Ordinary vocabulary-head answers, auxiliary absent from inference. Deadline Oct16 17:00 KST. Cost is not quality; previous source and weights preserved.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bnWb_grounded_span_strict_answers_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_grounded_span_execution.py --mode evaluate --execute --max-wall-sec 5400
