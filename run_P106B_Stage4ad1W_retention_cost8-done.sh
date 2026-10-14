#!/usr/bin/env bash
# Fresh corpus required. Eight measured updates, no checkpoint/quality claim. About 0.05h GPU.
# Same SFT micro8 accum16 ckptON plus native8 rows per update, objective weight0.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ad1W_retention_cost8_"${stamp}" --note 'Cost8 only. Same native CE computation in every arm; weight0 has no native objective. No checkpoint; 17:00 KST authority bound. Read real tokens separately from padding.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ad1W_retention_cost8_"${stamp}" -- "$python_bin" -B -X utf8 scripts/diag_p106b_retention_course.py --mode cost --arm sft_only --execute --max-wall-sec 600
