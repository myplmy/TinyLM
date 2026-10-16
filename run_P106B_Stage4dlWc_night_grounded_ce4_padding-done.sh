#!/usr/bin/env bash
# Attempt complete; result/raw/code identity preserved, not an automatic quality PASS.
# V2 same E970 two-view CE plus balanced replay/native640, both real cost gates required.
# Estimated 1.7h, GPU alone when applicable; real cost gates control full trials.
# Matched micro8 accum16 seq1024 checkpointON compiledefault; no stdin/downloads.
# One-time overnight authority ends2026-10-17 10:00 KST, training stops09:00.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dlWc_night_grounded_ce4_padding_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dlWc_night_grounded_ce4_padding_"$run_stamp" --num 101 --note 'V2 same E970 two-view CE plus balanced replay/native640, both real cost gates required. Cost/static success is not free-answer intelligence. Read actual masks/targets, complete steps, raw answers and retention separately. Original V1 error preserved; no protected source/external publication.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dlWc_night_grounded_ce4_padding_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_train.py --mode train --arm ce --max-wall-sec 14400 --execute
