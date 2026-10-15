#!/usr/bin/env bash
# Completed CPU17 plus two nonloading check-only calls; raw005142 preserved.
# Deadline Oct16 17:00 KST,45minute closing margin. No stdin or global queue.
# No protected data/download/old overwrite. Teacher reasoning excluded from student.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bs0W_dualqa_course_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0W_dualqa_course_cpu_"$run_stamp" --num 101 --note 'CPU17 checks only; whole-update gradient/mask and actual-history paths; no GPU. Fresh namespace only; first attempts and actual history retained. Whole smoke is user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0W_dualqa_course_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_dualqa_course.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0W_dualqa_course_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_dualqa_curriculum.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0W_dualqa_course_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_dualqa_eval.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0W_dualqa_course_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_curriculum.py --mode cost --check-only
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0W_dualqa_course_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_eval.py --check-only
