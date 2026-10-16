#!/usr/bin/env bash
# Actual cost8 completed exit0; raw110602, checkpoint0. Full216 is a separate stage.
# Fixed-parent source repair crossed with code role bridge; independent recipe study.
# Expected CPU seconds or GPU minutes; exact bounds in plan and commands below.
# Fail closed only for this stage's dependencies; no stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4coWb_repair_repeat_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4coWb_repair_repeat_cost8_"$run_stamp" --num 101 --note 'Same parent and batch, cost8 only. No checkpoint. Four same-code costs required before full216/evaluation/closure budget. Complete raw/canonical private shards below20MB. Full smoke user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4coWb_repair_repeat_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_repair_role_train.py --mode cost --arm repair_repeat --max-wall-sec 1800 --execute
