#!/usr/bin/env bash
# CPU fresh sequence, stale/fatal rejection and restoration; no model or device calls
# No stdin, installs, old mutation or automatic adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4p0W_memory_stream_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw log; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4p0W_memory_stream_cpu_"$run_stamp" --num 101 --note 'CPU fresh sequence, stale/fatal rejection and restoration; no model or device calls. Sample arrival age is not hardware timestamp; no continuous peak/OOM or semantic PASS. GPT execution authorized only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4p0W_memory_stream_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_memory_stream scripts.test_p106b_gemma_telemetry_resume
