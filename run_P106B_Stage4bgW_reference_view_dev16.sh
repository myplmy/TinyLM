#!/usr/bin/env bash
# Same selected student and16 dev questions: full, teacher-selected whole messages, empty reference.
# No learning, teacher calls, checkpoint writes, online judgment or training export.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bgW_reference_view_dev16_"$stamp" --note 'Same weights/questions, full/selected/empty reference only. Teacher agreement not truth. Entire upstream metadata retained privately; dev rows never exported for training.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bgW_reference_view_dev16_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_reference_views.py --execute --max-wall-sec 600
