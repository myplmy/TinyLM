#!/usr/bin/env bash
# Executed20261017; raw status and exact commands retained before cleanup.
# Original P090B, fixed QA/assistant/native consumers; extra body-LM beta0/.1.
# Own CPU and both actual8 cost gates precede full640; no stdin/downloads.
# One-time authority2026-10-17 10:00KST, GPU ends09:00; old source preserved.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dsWa_night_prompt0_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dsWa_night_prompt0_cost8_"$run_stamp" --num 101 --note 'Separate natural context/question LM mean only. Original assistant masks/CE denominator/native replay and source/order stay fixed. Both betas calculate the same prompt head. Repeated processed tokens and extra supervised positions are not new unique data or300M SFT. CPU/cost success is not actual answer quality. Final4 primary, DEV representative separate;09:00 stop.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dsWa_night_prompt0_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_prompt.py --mode cost --arm prompt0 --max-wall-sec 1800 --execute
