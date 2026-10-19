#!/usr/bin/env bash
# P106B_Stage4fcWa_current_native_ternary_mc: exact cached public pack, current six weights, cached Falcon MC reference.
# No training, checkpoint writes, source mutation, download, stdin, or official harness parity claim.
# Same sum-NLL primary, char-normalized secondary, no-PMI; free greedy128/FP32 MATH/KV-on.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fcWa_current_native_ternary_mc_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fcWa_current_native_ternary_mc_"$run_stamp" --num 101 --note 'Regression35, all six original training receipts/checkpoints, exact cached public/Falcon IDs and source code are prerequisites. Requested9216/scored9212 across all stages; preserve four KorQuAD length exclusions. Same sum-NLL primary, char normalization separate, no-PMI, greedy128/FP32 MATH/KV-on. Total activity bound3600s, record reserve600s. This stage cap1200s GPU=Y; no new Falcon call, training, CP, or quality automatic adoption.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fcWa_current_native_ternary_mc_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_current_benchmark.py --mode evaluate --model-id native_ternary --max-wall-sec 1200 --execute
