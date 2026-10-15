#!/usr/bin/env bash
# Measured p95 forecast for pair416 each, evaluation900 and closure2700 seconds before17.
# Independent namespace, no stdin, no implicit resume or old checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aw0Wc_state_budget_"$stamp" --note 'Measured p95 forecast for pair416 each, evaluation900 and closure2700 seconds before17.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aw0Wc_state_budget_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_state_update_aux.py --mode budget --execute
