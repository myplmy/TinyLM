#!/usr/bin/env bash
# CPU paired fixed-model roots; all fresh student collections must already exist.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4axWb_state_pair_readback_"$stamp" --note 'CPU complete state raw pairing; no model, new learning or implicit quality promotion.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4axWb_state_pair_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/summarize_p106b_structured_pair.py --tag p106b_state_update_aux_v1_s1337 --execute
