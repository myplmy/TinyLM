#!/usr/bin/env bash
# CPU exact Unicode support spans/IDs, student-visible bytes and shared3-attempt budget
# No stdin/download/old corpus mutation; source IDs are not semantic verification.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4s0W_visible_source_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve existing raw; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4s0W_visible_source_cpu_"$run_stamp" --num 101 --note 'CPU exact Unicode support spans/IDs, student-visible bytes and shared3-attempt budget. Same card sampler/8K/3072/1024, structural retries only. Read full question/answer/reference and cost; no automatic bulk adoption. GPT run only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4s0W_visible_source_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_visible_source
