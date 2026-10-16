#!/usr/bin/env bash
# Closed actual execution; exact scope/raw result preserved, not global quality PASS.
# Read-only exploratory scores; no interactive stdin or learning.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eiWd_unique_question_scores_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eiWd_unique_question_scores_"$run_stamp" --num 101 --note 'After both cost reports and budget, unique32k final complete same110 source bundles. Relative likelihood is not answer generation success, truth or architecture causality.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eiWd_unique_question_scores_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_question_scores.py --mode full --endpoint unique32k --execute
