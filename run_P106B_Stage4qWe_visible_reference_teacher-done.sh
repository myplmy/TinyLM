#!/usr/bin/env bash
# GemmaMTP8 visible-reference or missing-info cases; no hidden context or student training
# Separate small quality experiment; unchanged75M x4epoch goal.
# No stdin, download, old mutation or protected data.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4qWe_visible_reference_teacher_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw log; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4qWe_visible_reference_teacher_"$run_stamp" --num 101 --note 'GemmaMTP8 visible-reference or missing-info cases; no hidden context or student training. Eight procedural types are not general world intelligence. Check actual answers, masks, tokens, nativeCE and cost separately. GPT execution authorized only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4qWe_visible_reference_teacher_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_context_quality.py --mode teacher --execute --max-wall-sec 300
