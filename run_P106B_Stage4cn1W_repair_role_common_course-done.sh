#!/usr/bin/env bash
# Completed 2026-10-16 10:54:46 KST; raw105332 exit0, four courses frozen.
# Fixed-parent source repair crossed with code role bridge; independent recipe study.
# Expected CPU seconds or GPU minutes; exact bounds in plan and commands below.
# Fail closed only for this stage's dependencies; no stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cn1W_repair_role_common_course_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cn1W_repair_role_common_course_"$run_stamp" --num 101 --note 'Actual accepted512 quota and operational teacher seal required. Freeze four6912-row recipes and fresh64; no CUDA. Complete raw/canonical private shards below20MB. Full smoke user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cn1W_repair_role_common_course_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_repair_role_course.py --execute
