#!/usr/bin/env bash
# Teacher-only MTP ON: same8 original sources, cap256/1024 in both orders. Actual fields unverified, no student/data admission.
# Fresh namespace, no stdin/implicit resume/old mutation; fail closed on prerequisite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ao1W_lossless_budget_panel_"$stamp" --note 'Teacher-only MTP ON: same8 original sources, cap256/1024 in both orders. Actual fields unverified, no student/data admission.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ao1W_lossless_budget_panel_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_verbatim_source.py --mode pilot --execute --max-wall-sec 1200
