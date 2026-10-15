#!/usr/bin/env bash
# Fresh4pass416 state/basic updates, no auxiliary gradient, native1. Deadline budget required.
# Independent namespace, no stdin, no implicit resume or old checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4awWa_state_zero4_"$stamp" --note 'Fresh4pass416 state/basic updates, no auxiliary gradient, native1. Deadline budget required.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4awWa_state_zero4_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_state_update_aux.py --mode train --arm aux0 --execute --max-wall-sec 3600
