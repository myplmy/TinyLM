#!/usr/bin/env bash
# Closed actual execution; exact scope/raw result preserved, not global quality PASS.
# New isolated complete-smoke observation; no stdin or old-output overwrite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ek0W_final_smoke_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ek0W_final_smoke_cpu_"$run_stamp" --num 101 --note 'CPU64 and actual unchanged smoke-module topology/argv/path contract only. No GPU/model loading/training, not full runtime smoke.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ek0W_final_smoke_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest -b scripts.test_p106b_night_question_bundles scripts.test_p106b_night_question_bundles_runtime scripts.test_p106b_night_question_bundles_v2 scripts.test_p106b_night_question_bundles_v3 scripts.test_p106b_night_question_scores scripts.test_p106b_night_question_scores_runtime scripts.test_p106b_night_final_smoke
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ek0W_final_smoke_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_final_smoke.py --mode check
