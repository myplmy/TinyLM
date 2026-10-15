#!/usr/bin/env bash
# Fresh4pass416 state/basic updates, correct updated-target bit1, native1. No inference head.
# Independent namespace, no stdin, no implicit resume or old checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4awWb_state_positive4_"$stamp" --note 'Fresh4pass416 state/basic updates, correct updated-target bit1, native1. No inference head.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4awWb_state_positive4_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_state_update_aux.py --mode train --arm aux100 --execute --max-wall-sec 3600
