#!/usr/bin/env bash
# Fictional relation fields and masked correction, plan P106B Stage4bx-bz.
# Deadline Oct16 17:00 KST,45minute margin. No stdin, original writes or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bx2Wb_relation_fact_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx2Wb_relation_fact_cost8_"$run_stamp" --num 101 --note 'Fact1 actual cost8, same parent/data. Fact selection is training-only, not a truth verifier. Current corpus is not75M/300M. Real-world/source quality and exact fictional oracle are separate. Full smoke is user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx2Wb_relation_fact_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_train.py --mode cost --arm fact1 --execute --max-wall-sec 3600
