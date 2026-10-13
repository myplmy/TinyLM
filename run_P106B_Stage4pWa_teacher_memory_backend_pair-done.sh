#!/usr/bin/env bash
# Teacher-only same24 requests; one-shot versus persistent2s memory query; no student training
# No stdin, installs, old mutation or automatic adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4pWa_teacher_memory_backend_pair_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw log; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4pWa_teacher_memory_backend_pair_"$run_stamp" --num 101 --note 'Teacher-only same24 requests; one-shot versus persistent2s memory query; no student training. Sample arrival age is not hardware timestamp; no continuous peak/OOM or semantic PASS. GPT execution authorized only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4pWa_teacher_memory_backend_pair_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_memory_query_pair.py --execute --max-wall-sec 900
