#!/usr/bin/env bash
# CPU29 and real64 source binding completed; models remain a separate gate.
# Same-instruction field-order probe; separate from held order-training study.
# No stdin/downloads/learning/checkpoint writes. CPU then two bounded models.
# Full six primary evaluations precede probe; GPU ends2026-10-17 09:00KST.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ee0W_order_probe_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ee0W_order_probe_cpu_"$run_stamp" --num 101 --note 'CPU29 plus exact already-frozen TEST64 source, same-instruction view1/3 and real prompt-token binding. No model forward/CUDA/training; old order-training gate remains HOLD. Full primary evaluations precede any later probe.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ee0W_order_probe_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest -b scripts.test_p106b_night_order_probe scripts.test_p106b_night_order_probe_runtime
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ee0W_order_probe_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_order_probe.py --mode freeze --max-wall-sec 900 --execute
