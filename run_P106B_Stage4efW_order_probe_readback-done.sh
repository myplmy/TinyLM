#!/usr/bin/env bash
# Closed actual execution; exact scope/raw result preserved, not global quality PASS.
# Same-instruction field-order probe; separate from held order-training study.
# No stdin/downloads/learning/checkpoint writes. CPU then two bounded models.
# Full six primary evaluations precede probe; GPU ends2026-10-17 09:00KST.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4efW_order_probe_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4efW_order_probe_readback_"$run_stamp" --num 101 --note 'CPU full two-model raw/source/body/checkpoint-path/primary-receipt recount. Within-model input-order effect only; repeat agreement and same wrong answers are not correctness or global model quality.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4efW_order_probe_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_order_probe.py --mode readback --max-wall-sec 900 --execute
