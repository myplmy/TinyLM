#!/usr/bin/env bash
# Attempt complete; result/raw/code identity preserved, not an automatic quality PASS.
# Freeze same explicit QA in V2 and verify real CPU padding IDs, masks and consumers.
# Estimated .08h, GPU alone when applicable; real cost gates control full trials.
# Matched micro8 accum16 seq1024 checkpointON compiledefault; no stdin/downloads.
# One-time overnight authority ends2026-10-17 10:00 KST, training stops09:00.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dk0Wb_night_grounded_padding_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0Wb_night_grounded_padding_cpu_"$run_stamp" --num 101 --note 'Freeze same explicit QA in V2 and verify real CPU padding IDs, masks and consumers. Cost/static success is not free-answer intelligence. Read actual masks/targets, complete steps, raw answers and retention separately. Original V1 error preserved; no protected source/external publication.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0Wb_night_grounded_padding_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_qa_data scripts.test_p106b_night_learning scripts.test_p106b_night_course scripts.test_p106b_night_train
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0Wb_night_grounded_padding_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_train.py --mode freeze --execute
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0Wb_night_grounded_padding_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_train.py --mode wire --execute
