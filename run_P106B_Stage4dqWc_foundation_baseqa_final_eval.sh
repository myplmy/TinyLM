#!/usr/bin/env bash
# Same fixed original-input QA/public/retention cohort; independent endpoint.
# Diagnostic only; no model writes or stdin. TEST never chooses checkpoints.
# Authority ends2026-10-17 10:00KST;09:00 GPU stop; old data preserved.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dqWc_foundation_baseqa_final_eval_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dqWc_foundation_baseqa_final_eval_"$run_stamp" --num 101 --note 'Same frozen512 QA/three wrappers, exact64 cube, complete actual/gold histories, original1920 public cohort and fixed native windows. Original P090B and same native continuation/QA640 recipe. Final4 primary; DEV-selected representative separate. Whole semantic truth, learning-seed variance and broad model adoption are not certified.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dqWc_foundation_baseqa_final_eval_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_eval_recovery.py --mode evaluate --endpoint base_qa --max-wall-sec 7200 --execute
