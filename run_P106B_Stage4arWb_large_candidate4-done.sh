#!/usr/bin/env bash
# Fresh same-parent dev-selected auxiliary, four passes2096 updates, rechecked deadline budget.
# Independent fresh outputs; explicit gates; no stdin, downloads or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4arWb_large_candidate4_"$stamp" --note 'Fresh same-parent dev-selected auxiliary, four passes2096 updates, rechecked deadline budget.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4arWb_large_candidate4_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_scale.py --mode train --arm candidate --execute --max-wall-sec 10800
