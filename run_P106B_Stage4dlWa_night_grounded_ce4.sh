#!/usr/bin/env bash
# Same E970 natural two-view CE plus balanced replay/native, four passes640 updates; cost pair required.
# Estimated 1.7h, one GPU only when applicable; actual cost gate controls full trials.
# Matched micro8 accum16 seq1024 checkpointON compiledefault; no stdin or downloads.
# Authorization ends 2026-10-17 10:00 KST; new training stops before09:00.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dlWa_night_grounded_ce4_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dlWa_night_grounded_ce4_"$run_stamp" --num 101 --note 'Same E970 natural two-view CE plus balanced replay/native, four passes640 updates; cost pair required. Read source/mask/actual target counts, completion and free-answer quality separately. Cost/static PASS is not intelligence. Old originals preserved; no protected source or external publication.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dlWa_night_grounded_ce4_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_train.py --mode train --arm ce --max-wall-sec 14400 --execute

