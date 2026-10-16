#!/usr/bin/env bash
# Freeze explicit natural QA and balanced replay, then verify actual CPU parent/masks and consumers; not quality.
# Estimated .08h, one GPU only when applicable; actual cost gate controls full trials.
# Matched micro8 accum16 seq1024 checkpointON compiledefault; no stdin or downloads.
# Authorization ends 2026-10-17 10:00 KST; new training stops before09:00.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dk0W_night_grounded_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0W_night_grounded_cpu_"$run_stamp" --num 101 --note 'Freeze explicit natural QA and balanced replay, then verify actual CPU parent/masks and consumers; not quality. Read source/mask/actual target counts, completion and free-answer quality separately. Cost/static PASS is not intelligence. Old originals preserved; no protected source or external publication.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0W_night_grounded_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_qa_data scripts.test_p106b_night_learning scripts.test_p106b_night_course scripts.test_p106b_night_train
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0W_night_grounded_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_train.py --mode freeze --execute
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dk0W_night_grounded_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_train.py --mode wire --execute
