#!/usr/bin/env bash
# Completed 2026-10-16 12:20:55 KST; raw115551 exit0, all5 fixed endpoints.
# Fixed-parent source repair crossed with code role bridge; independent recipe study.
# Expected CPU seconds or GPU minutes; exact bounds in plan and commands below.
# Fail closed only for this stage's dependencies; no stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cqW_repair_role_actual_evaluation_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cqW_repair_role_actual_evaluation_"$run_stamp" --num 101 --note 'Fixed parent plus fourfinals. Fresh64 actual/gold separate; neutral-role styles and retention. FP32 greedy64; no teacher or optimization. Complete raw/canonical private shards below20MB. Full smoke user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cqW_repair_role_actual_evaluation_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_repair_role_evaluate.py --mode evaluate --max-wall-sec 3600 --execute
