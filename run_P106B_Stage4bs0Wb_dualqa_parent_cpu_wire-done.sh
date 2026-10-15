#!/usr/bin/env bash
# Completed actual parent CPU wire, raw010854 exit0; commands retained here.
# Fresh small receipt namespace; frozen teacher/student source modules unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bs0Wb_dualqa_parent_cpu_wire_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0Wb_dualqa_parent_cpu_wire_"$run_stamp" --num 101 --note 'CPU-only actual Source0 parent geometry/body hash and known3072 code labels. CUDA initialized false, forwards0, optimizer0, checkpoints0. Does not complete student corpus or prove quality; teacher generation remains independent.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bs0Wb_dualqa_parent_cpu_wire_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_parent_wire.py --execute
