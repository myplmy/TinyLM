#!/usr/bin/env bash
# P106B_Stage4eyWh_broad_order_readback: fixed source/update groups, mixed versus staged order.
# No stdin, download, old mutation, or automatic model-quality verdict.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eyWh_broad_order_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eyWh_broad_order_readback_"$run_stamp" --num 101 --note 'Regression, exact source/consumer and final receipt required. Same22528 rows, two passes352 updates, m8a16ckptON. Native binding is absolute-update. Old monitor and new actual-history dialogues are separate. Cost callers require five-minute idle. Estimated.17h GPU=N, worker cap600s.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eyWh_broad_order_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_broad_curriculum.py --mode readback --max-wall-sec 600 --execute
