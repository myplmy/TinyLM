#!/usr/bin/env bash
# Teacher-only selected cap256, original messages/indentation intact. Same512/64 cohort regenerated, not new unique concepts.
# Completed2026-10-15 raw090609 exit0;576 original-message sources, thinking256.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4apW_verbatim_teacher_course_"$stamp" --note 'Teacher-only experimental cap256 selected from same8 source/both-order pilot, not quality equivalence or global default. Original messages/indentation intact. Same512/64 cohort regenerated, not new unique concepts.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4apW_verbatim_teacher_course_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_verbatim_source.py --mode generate --thinking 256 --execute --max-wall-sec 7200
