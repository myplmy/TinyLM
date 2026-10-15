#!/usr/bin/env bash
# Completed CPU5/DEV-only lock raw023247 before TEST; epoch2/epoch2 chosen.
# Does not replace final4epoch primary; no GPU, new training or checkpoint.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bv0W_devbest_checkpoint_lock_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bv0W_devbest_checkpoint_lock_"$run_stamp" --num 101 --note 'CPU choice only: minimum source DEV CE among saved epochs1..4, early tie. Lock before fresh TEST; code/native/TEST scores do not select. Final4epoch remains primary; no model/GPU/training/checkpoint.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bv0W_devbest_checkpoint_lock_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_dualqa_checkpoint_choice.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bv0W_devbest_checkpoint_lock_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_checkpoint_choice.py --execute
