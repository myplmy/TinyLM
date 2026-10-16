#!/usr/bin/env bash
# Closed attempt: CPU26 passed, actual census failed before writing at20MB limit.
# Source-only census, no model/forward/GPU. No interactive input.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eh0W_question_bundles_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eh0W_question_bundles_cpu_"$run_stamp" --num 101 --note 'CPU26 synthetic regression and source-only TRAIN32k/TEST512 exact-context question-bundle census. Raw context SHA separates normalized identity variants. Character-distinct candidates are not semantic negatives/training data. No model/GPU/source answer-based selection.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eh0W_question_bundles_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest -b scripts.test_p106b_night_question_bundles scripts.test_p106b_night_question_bundles_runtime
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eh0W_question_bundles_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_question_bundles.py --mode freeze --execute
