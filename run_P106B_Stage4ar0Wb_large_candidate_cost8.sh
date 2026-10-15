#!/usr/bin/env bash
# Eight dev-selected auxiliary cost updates. No checkpoint.
# Independent fresh outputs; explicit gates; no stdin, downloads or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ar0Wb_large_candidate_cost8_"$stamp" --note 'Eight dev-selected auxiliary cost updates. No checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ar0Wb_large_candidate_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_scale.py --mode cost --arm candidate --execute --max-wall-sec 900
