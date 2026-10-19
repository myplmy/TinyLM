#!/usr/bin/env bash
# GATED main3x1758 and completed R; actual prefix hash authentication only.
# No model, CUDA, training, checkpoint writes, network, or stdin interaction.
# Actual CPU source workers: two x at most300s; regression/wrapper are separate.
# Partial prerequisites HOLD8; source/tool failures9; never a quality PASS.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4erS_actual_prefix_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
export CUDA_VISIBLE_DEVICES=
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4erS_actual_prefix_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_actual_prefix_readback.py --mode readback --max-wall-sec 300 --execute
