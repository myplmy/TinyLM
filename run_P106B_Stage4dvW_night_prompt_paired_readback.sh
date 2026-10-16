#!/usr/bin/env bash
# Same scientific cohort, repeated development evaluation; no stdin/training.
# Final4 and separate DEV-min representative, never TEST-selected.
# One-time authority2026-10-17 10:00KST, GPU ends09:00; original raw preserved.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dvW_night_prompt_paired_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dvW_night_prompt_paired_readback_"$run_stamp" --num 101 --note 'Prompt-LM evaluation binding, exact same source/CASE and FP32 MATH generation. Four endpoints include final4 primary and separate DEV selection. Whole raw/receipt/native denominator proof required; repeated development cohort, no official benchmark or broad intelligence certificate. No training/checkpoint writes/downloads;09:00 stop.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dvW_night_prompt_paired_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_prompt_eval.py --mode readback --max-wall-sec 7200 --execute
