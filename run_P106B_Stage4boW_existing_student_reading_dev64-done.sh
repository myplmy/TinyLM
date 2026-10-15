#!/usr/bin/env bash
# Existing trained students on same source DEV64. No training/checkpoint writes.
# Previous test is explicitly development now; cached parent/span0 are reused.
# CPU fixture precedes actual GPU; no stdin/download/source or weight mutations.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4boW_existing_student_reading_dev64_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve previous raw evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4boW_existing_student_reading_dev64_"$run_stamp" --num 101 --note 'CPU fixture then existing three students actual DEV64, while parent/span0 identical outputs are reused. New training/weights0. Source literal/F1 and actual source reading are distinct. Different training histories permit descriptive initializer comparisons only. Deadline Oct16 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4boW_existing_student_reading_dev64_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_foundation_panel.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4boW_existing_student_reading_dev64_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_foundation_panel.py --execute --max-wall-sec 1800
