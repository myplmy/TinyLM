#!/usr/bin/env bash
# P070B Stage1Wb: CPU counterfactual observation, not a new acceptance threshold.
# Preserve old ERROR9. No GPU, optimizer, checkpoint write, stdin or old mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/105_log_$(date +%Y%m%d)_P070B_Stage1Wb_prefill_shape_cause_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage1Wb_prefill_shape_cause_cpu_"$run_stamp" --num 105 --note 'CPU1 FP32-MATH same reverse-R2 weights and old failure9IDs. Observe full9/prefix3, equal-shape cache flags and changed future IDs separately. Six raw arrays/seven contrasts; fixed original1e-5/1e-4 tolerance. Observation completion is NOT old gate PASS or language quality. Worker120s within original600s ceiling and end08Z with600s reserve; no GPU/update/CP write.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage1Wb_prefill_shape_cause_cpu_"$run_stamp" --num 105 -- "$python_bin" -B -X utf8 scripts/diag_p070b_prefill_shape_cause.py --max-wall-sec 120 --execute
