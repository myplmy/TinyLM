#!/usr/bin/env bash
# Closed actual CPU6 and two-body causal-prefix check; no GPU, learning or checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4elW_cpu_causal_prefix_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4elW_cpu_causal_prefix_"$run_stamp" --num 101 --note 'CPU6 then fixed original4 bundles, same two checkpoint bodies; full future-answer inputs versus actual answer-free prefix. FP32 MATH; CUDA never initialized; no learning or checkpoint writes; <=600 seconds.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4elW_cpu_causal_prefix_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest -b scripts.test_p106b_night_causal_readback
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4elW_cpu_causal_prefix_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_causal_readback.py --execute
