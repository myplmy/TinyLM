#!/usr/bin/env bash
# Fictional relation fields and masked correction, plan P106B Stage4bx-bz.
# Deadline Oct16 17:00 KST,45minute margin. No stdin, original writes or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bx0W_relation_cpu_contract_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx0W_relation_cpu_contract_"$run_stamp" --num 101 --note 'CPU27 plus no-loading check-only; old wrong answer is context, not target. Current corpus is not75M/300M. Real-world/source quality and exact fictional oracle are separate. Full smoke is user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx0W_relation_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_fields.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx0W_relation_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_auxiliary.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx0W_relation_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_course.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx0W_relation_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_train.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx0W_relation_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_course.py --check-only
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bx0W_relation_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_train.py --mode cost --arm fact1 --check-only
