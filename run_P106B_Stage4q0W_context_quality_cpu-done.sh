#!/usr/bin/env bash
# CPU procedural roots/splits, visible-reference prompt and assistant-turn MTP
# Separate small quality experiment; unchanged75M x4epoch goal.
# No stdin, download, old mutation or protected data.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4q0W_context_quality_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw log; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4q0W_context_quality_cpu_"$run_stamp" --num 101 --note 'CPU procedural roots/splits, visible-reference prompt and assistant-turn MTP. Eight procedural types are not general world intelligence. Check actual answers, masks, tokens, nativeCE and cost separately. GPT execution authorized only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4q0W_context_quality_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_context_quality scripts.test_p101a_sft_mtp
