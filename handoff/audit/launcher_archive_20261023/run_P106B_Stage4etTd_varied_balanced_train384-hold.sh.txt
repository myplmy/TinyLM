#!/usr/bin/env bash
# Superseded v1 driver was frozen in git d216de4; original commands are historical only.
printf '%s\n' '[HOLD] Superseded v1 launcher; use the separately versioned Stage4eu plan. No child/model started.' >&2
exit 8
# HOLD v1: preserved CPU corpus has a consumer mask-owner incompatibility. Use the separately versioned recovery.
# Question wording x position study; original P090B parent, same targets and native windows.
# micro8 accum16 seq1024 checkpointON compile-default; CE-only; no teacher or MTP.
# train bounded 7200s; train requires all four actual cost8 receipts.
# CPU/GPU authority ends Oct20 17:00 KST; reserve evaluation and records.
# REGRESSION/PREFLIGHT/EXECUTE; HOLD8/ERROR9/interrupt130 are not answer-quality verdicts.
# One stage exits on failure; run_queue retains independent selected experiments.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4etTd_varied_balanced_train384_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4etTd_varied_balanced_train384_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_question_transfer.py --mode train --arm varied_balanced --max-wall-sec 7200 --execute
