#!/usr/bin/env bash
# P106B_Stage4fbWb_native_float_to_ternary: fixed weights, trained route closed before other inference route.
# No training, checkpoint writes, source mutation, downloads or stdin.
# Same1694 per off-diagonal; preserve failed phases, stop dependent stages only.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fbWb_native_float_to_ternary_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fbWb_native_float_to_ternary_"$run_stamp" --num 101 --note 'Regression28 and four completed native/SFT checkpoints plus four diagonal raw receipts are required. CPU strict original route is closed before explicit counterfactual route. Same greedy64/FP32 MATH/KV-on; zero learning/CP. Read native and SFT separately, reused6776 and fresh6776 separately. Estimated upper bound .5h GPU=D, worker cap1800s; not a general-quality verdict.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fbWb_native_float_to_ternary_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_route_cross_readout.py --mode evaluate --trained-mode float --inference-mode ternary --endpoint native --max-wall-sec 1800 --execute
