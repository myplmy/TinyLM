#!/usr/bin/env bash
# Original-QA curriculum, immutable input/new outputs, no stdin or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cgWb_original_three_repeat4_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cgWb_original_three_repeat4_"$run_stamp" --num 101 --note 'After costs/budget: original three-QA four epochs200; extra information/targets explicitly reported, not a pure-format effect. No world-truth certification. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cgWb_original_three_repeat4_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_original_qa3_train.py --mode train --arm three --execute --max-wall-sec 7200
