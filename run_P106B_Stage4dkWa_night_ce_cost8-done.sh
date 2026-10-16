#!/usr/bin/env bash
# Attempt completed; original V1 raw logs preserved; not a quality PASS.
# CE arm cost8 only, no checkpoint; actual finite gradient and matched exposure.
# Estimated .15h, one GPU only when applicable; actual cost gate controls full trials.
# Matched micro8 accum16 seq1024 checkpointON compiledefault; no stdin or downloads.
# Authorization ends 2026-10-17 10:00 KST; new training stops before09:00.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dkWa_night_ce_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dkWa_night_ce_cost8_"$run_stamp" --num 101 --note 'CE arm cost8 only, no checkpoint; actual finite gradient and matched exposure. Read source/mask/actual target counts, completion and free-answer quality separately. Cost/static PASS is not intelligence. Old originals preserved; no protected source or external publication.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dkWa_night_ce_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_train.py --mode cost --arm ce --max-wall-sec 1800 --execute
