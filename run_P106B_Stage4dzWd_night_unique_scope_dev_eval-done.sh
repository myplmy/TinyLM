#!/usr/bin/env bash
# Complete separate DEV4 read-only decode; same final checkpoint and outputs.
# New budget scope only: original32k courses, loss,640 updates and512-case eval unchanged.
# Actual new CPU/cost8 required; original bare-full/input-order HOLD is not completed.
# One-time approval ends2026-10-17 10:00KST; GPU stops09:00KST.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dzWd_night_unique_scope_dev_eval_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dzWd_night_unique_scope_dev_eval_"$run_stamp" --num 101 --note 'New independent budget scope, same source32k once versus old8k four passes, full640/micro8 accum16/ckpt-on and same actual tokenizer/masks/parent/LR. New CPU and cost8 precede train. Old full-parent/order gates remain HOLD. Real tokens, supervision, unique roots and padded slots are separate; no general intelligence or300M SFT claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dzWd_night_unique_scope_dev_eval_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_diversity_scope_eval_v2.py --mode evaluate --endpoint unique32k_best --max-wall-sec 7200 --execute
