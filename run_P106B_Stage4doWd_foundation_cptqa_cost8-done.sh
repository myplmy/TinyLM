#!/usr/bin/env bash
# Completed once; archive exact commands and source before cleanup.
# Completed native parent QA8 cost, new moments and same QA consumers; no checkpoint.
# Estimate .05h; actual cost must fit all remaining QA/evaluation before09:00.
# Native CPT is not300M SFT; no old asset changes/downloads/interactive input.
# One-time user authority ends2026-10-17 10:00KST; micro8 accum16 seq1024 ckptON.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4doWd_foundation_cptqa_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4doWd_foundation_cptqa_cost8_"$run_stamp" --num 101 --note 'Completed native parent QA8 cost, new moments and same QA consumers; no checkpoint. Read exact processed/native/assistant denominators, DEV vs TEST and actual answers separately. Additional native data may overlap prior parent exposure. No original checkpoint overwrite, downloads, protected data or automatic truth certification.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4doWd_foundation_cptqa_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_foundation.py --mode cost --arm cpt_qa --max-wall-sec 1800 --execute
