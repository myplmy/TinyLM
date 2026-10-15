#!/usr/bin/env bash
# New interleaved relation schedule; no old data/CODE/CPT overwrite or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cb0W_interleave_cpu_contract_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0W_interleave_cpu_contract_"$run_stamp" --num 101 --note 'CPU15: same canonical multiset, balanced views, wrong first answer mask, identical trainer function AST and no-loading checks. Not75M/300M or world intelligence. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0W_interleave_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_interleaved_schedule.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0W_interleave_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_interleaved_course.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0W_interleave_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_interleaved_train.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0W_interleave_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_course.py --check-only
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb0W_interleave_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_train.py --mode cost --arm fact1 --check-only
