#!/usr/bin/env bash
# Same-instruction field-order probe; separate from held order-training study.
# No stdin/downloads/learning/checkpoint writes. CPU then two bounded models.
# Full six primary evaluations precede probe; GPU ends2026-10-17 09:00KST.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eeWb_unique32k_order_probe_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eeWb_unique32k_order_probe_"$run_stamp" --num 101 --note 'Read-only final unique32k model, same64 source and view1/3. Full primary six evaluations and baseQA receipts first; no source reselection, training, new weights or old gate credit. GPU ends09:00.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eeWb_unique32k_order_probe_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_order_probe.py --mode evaluate --endpoint unique32k --max-wall-sec 900 --execute
