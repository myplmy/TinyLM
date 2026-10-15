#!/usr/bin/env bash
# Exposure-matched two-QA curriculum; plan P106B Stage4bs-bu.
# Deadline Oct16 17:00 KST,45minute closing margin. No stdin or global queue.
# No protected data/download/old overwrite. Teacher reasoning excluded from student.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bs2Wa_dualqa_repeat_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs2Wa_dualqa_repeat_cost8_"$run_stamp" --num 101 --note 'Repeat arm cost8 only; same Source0 parent, micro8 accum16 ckptON; checkpoint0. Fresh namespace only; first attempts and actual history retained. Whole smoke is user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs2Wa_dualqa_repeat_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_curriculum.py --mode cost --arm repeat --execute --max-wall-sec 3600
