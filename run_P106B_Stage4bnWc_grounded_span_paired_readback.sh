#!/usr/bin/env bash
# CPU only: exact source/prompt matching, literal metrics and fixed-model root CI.
# Model/teacher/GPU0; semantic review and automatic selection NOT_RUN.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bnWc_grounded_span_paired_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bnWc_grounded_span_paired_readback_"$run_stamp" --num 101 --note 'CPU readback of sealed same-question three-endpoint test256. Literal/F1 is not semantic truth. Root CI is not training-seed variance. Fixed8 review packet is local only; no automatic rejection or model selection.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bnWc_grounded_span_paired_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_summarize_p106b_grounded_span.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bnWc_grounded_span_paired_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/summarize_p106b_grounded_span.py --execute
