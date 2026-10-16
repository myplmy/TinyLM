#!/usr/bin/env bash
# Fixed-parent source repair crossed with code role bridge; independent recipe study.
# Expected CPU seconds or GPU minutes; exact bounds in plan and commands below.
# Fail closed only for this stage's dependencies; no stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cpWb_repair_repeat_full216_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cpWb_repair_repeat_full216_"$run_stamp" --num 101 --note 'Same parent, micro8 accum16 cp-on, additional4passes,216 updates; final-only checkpoint. No MTP, fact head or teacher concurrency. Not main300M. Complete raw/canonical private shards below20MB. Full smoke user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cpWb_repair_repeat_full216_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_repair_role_train.py --mode train --arm repair_repeat --max-wall-sec 5400 --execute
