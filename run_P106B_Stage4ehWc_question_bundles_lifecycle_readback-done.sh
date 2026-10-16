#!/usr/bin/env bash
# Complete ten full raw labels/nine unique checkpoints; no new generation.
# CPU existing-output readback only; all ten complete labels required.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ehWc_question_bundles_lifecycle_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ehWc_question_bundles_lifecycle_readback_"$run_stamp" --num 101 --note 'Recount all actual512x3 source-bound answers for foundation4/prompt4/unique2. Missing endpoints never filled with zeros; same checkpoint aliases not independent models. No new model/logits/generation/training/automatic quality rejection.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ehWc_question_bundles_lifecycle_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_question_bundles_v3.py --mode readback --execute
