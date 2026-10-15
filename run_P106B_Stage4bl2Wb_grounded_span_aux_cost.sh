#!/usr/bin/env bash
# New Oct16 study: source-only alignment, ordinary vocabulary-head answers.
# Plan P106B Stage4bl-bn; prior artifacts read-only; explicit deadline and fresh paths.
# CPU contract then corpus then two cost8 then paired training then answers.
# Training micro8 accum16 ckptON; no stdin, teacher, download, global smoke or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bl2Wb_grounded_span_aux_cost_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bl2Wb_grounded_span_aux_cost_"$run_stamp" --num 101 --note 'P106B grounded source study. Read actual unpadded/assistant/native counts, source truth UNVERIFIED, span head never used in generation. Cost8 is not quality; output and finish reason decide reported scope. Deadline Oct16 17:00 KST; originals preserved.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bl2Wb_grounded_span_aux_cost_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_grounded_span.py --mode cost --arm span03 --execute --max-wall-sec 1800
