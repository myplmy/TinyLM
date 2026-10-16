#!/usr/bin/env bash
# Closed actual execution; exact scope/raw result preserved, not global quality PASS.
# Read-only exploratory scores; no interactive stdin or learning.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ei0W_question_scores_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ei0W_question_scores_cpu_"$run_stamp" --num 101 --note 'CPU25 and actual unchanged110 source bundles: exact shifted content/EOT, same-answer target IDs, row-aligned <=20MB wire, fresh09 time clamp. No model/CUDA initialization/teacher/training.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ei0W_question_scores_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest -b scripts.test_p106b_night_question_scores scripts.test_p106b_night_question_scores_runtime
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ei0W_question_scores_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_question_scores.py --mode freeze --execute
