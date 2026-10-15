#!/usr/bin/env bash
# After both state arms: parent/students new1024, changed/copy baselines, native and real two-turn dialogues.
# Independent namespace, no stdin, no implicit resume or old checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4axW_state_update_readback_"$stamp" --note 'After both state arms: parent/students new1024, changed/copy baselines, native and real two-turn dialogues.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4axW_state_update_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_state_update_aux.py --mode evaluate --execute --max-wall-sec 1800
