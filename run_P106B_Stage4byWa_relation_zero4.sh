#!/usr/bin/env bash
# Fictional relation fields and masked correction, plan P106B Stage4bx-bz.
# Deadline Oct16 17:00 KST,45minute margin. No stdin, original writes or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4byWa_relation_zero4_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4byWa_relation_zero4_"$run_stamp" --num 101 --note 'After both cost8 and budget: fact0 four epochs688. Fresh weights only; source/native counts separate. Current corpus is not75M/300M. Real-world/source quality and exact fictional oracle are separate. Full smoke is user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4byWa_relation_zero4_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_train.py --mode train --arm fact0 --execute --max-wall-sec 10800
