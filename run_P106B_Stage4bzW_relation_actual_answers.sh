#!/usr/bin/env bash
# Independent relation course, P106B Stage4bx-bz; no stdin or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bzW_relation_actual_answers_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bzW_relation_actual_answers_"$run_stamp" --num 101 --note 'Parent/fact0/fact1 final4epoch. Actual3072, supplied-error512 and gold1536 per endpoint; fresh public128. Heads are not used for generation. Not75M/300M or general intelligence. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bzW_relation_actual_answers_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_evaluation.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bzW_relation_actual_answers_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_evaluate.py --mode evaluate --execute --max-wall-sec 10800
