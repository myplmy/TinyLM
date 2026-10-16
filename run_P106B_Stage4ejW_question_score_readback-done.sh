#!/usr/bin/env bash
# Closed actual execution; exact scope/raw result preserved, not global quality PASS.
# Read-only exploratory scores; no interactive stdin or learning.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ejW_question_score_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ejW_question_score_readback_"$run_stamp" --num 101 --note 'CPU independent two-model full raw/source/body/checkpoint recount. Fixed-answer question gaps, no new logits/generation/training/weights. Source110 is an exploratory repeated development cohort.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ejW_question_score_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_question_scores.py --mode readback --execute
