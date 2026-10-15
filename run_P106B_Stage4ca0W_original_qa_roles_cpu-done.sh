#!/usr/bin/env bash
# Old TRAIN2048-only CPU inventory. No teacher, model, corpus, or fresh TEST.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ca0W_original_qa_roles_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ca0W_original_qa_roles_cpu_"$run_stamp" --num 101 --note 'CPU6 plus no-loading check-only and existing TRAIN source inventory. Three original QA roles do not certify truth, translation, or new facts. No corpus/student generation or fresh TEST access. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ca0W_original_qa_roles_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_public_qa_roles.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ca0W_original_qa_roles_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_public_qa_role_inventory.py --check-only
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ca0W_original_qa_roles_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_public_qa_role_inventory.py --execute
