#!/usr/bin/env bash
# P070B Stage1Wa: actual pinned R1 checkpoint CPU function gate, not R2 training.
# No GPU, optimizer update, checkpoint write, stdin, downloads or product changes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/105_log_$(date +%Y%m%d)_P070B_Stage1Wa_full_checkpoint_cache_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage1Wa_full_checkpoint_cache_cpu_"$run_stamp" --num 105 --note 'CPU1 FP32-MATH: same pinned full R1 native checkpoint, product/fixed R1 and fixed uniform/reverse/shuffle R2 cache parity, KV/route binding and one NTP backward. No optimizer/GPU/checkpoint save, semantic grading, p95 adoption or R2 training. Worker cap600s; fixed tolerance; raw arrays ignored and public reports below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P070B_Stage1Wa_full_checkpoint_cache_cpu_"$run_stamp" --num 105 -- "$python_bin" -B -X utf8 scripts/diag_p070b_full_checkpoint_cpu.py --max-wall-sec 600 --execute
