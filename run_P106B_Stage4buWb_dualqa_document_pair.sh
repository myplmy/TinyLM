#!/usr/bin/env bash
# CPU-only after actual1024/gold512 replies at all three endpoints.
# Whole-document paired resampling, fixed source sample; no semantic grading.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4buWb_dualqa_document_pair_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4buWb_dualqa_document_pair_"$run_stamp" --num 101 --note 'CPU raw-event recheck, clustered by whole document root. Source pseudo-target equality is not semantic truth. Actual student and gold histories separate; fixed eight source contexts/48actual answers prepared for offline reading. Models0/training0.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4buWb_dualqa_document_pair_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_summarize_p106b_dualqa_eval.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4buWb_dualqa_document_pair_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/summarize_p106b_dualqa_eval.py --execute
