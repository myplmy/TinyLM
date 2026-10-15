#!/usr/bin/env bash
# Original-QA curriculum, immutable input/new outputs, no stdin or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cf0W_original_qa3_cpu_contract_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf0W_original_qa3_cpu_contract_"$run_stamp" --num 101 --note 'CPU10: first pair identical, original three roles/masks, partial last batch, real native reader and missing marker rejection, same gradient accumulation. No world-truth certification. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf0W_original_qa3_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_original_qa3_course.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf0W_original_qa3_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_original_qa3_train.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf0W_original_qa3_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_original_qa3_course.py --check-only
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf0W_original_qa3_cpu_contract_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_original_qa3_train.py --mode cost --arm three --check-only
