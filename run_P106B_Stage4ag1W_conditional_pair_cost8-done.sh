#!/usr/bin/env bash
# Same-code pairs required. Eight updates, no checkpoint. About0.05h GPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ag1W_conditional_pair_cost8_"$stamp" --note 'Cost8 with beta0 and identical negative/native computation. No checkpoint or quality verdict. Pair-only input and targets are separate from positive SFT exposure.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ag1W_conditional_pair_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_conditional_orpo.py --mode cost --arm pair_zero --execute --max-wall-sec 600
