#!/usr/bin/env bash
# Measured nearest-rank p95 forecast with evaluation and closure margins before17.
# Independent fresh outputs; explicit gates; no stdin, downloads or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ar0Wc_large_budget_"$stamp" --note 'Measured nearest-rank p95 forecast with evaluation and closure margins before17.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ar0Wc_large_budget_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_scale.py --mode budget --execute
