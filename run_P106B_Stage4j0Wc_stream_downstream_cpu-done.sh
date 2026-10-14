#!/usr/bin/env bash
# CPU newstream-v5 downstream namespace and no-teacher dispatch fixture
# Estimated 0.02h; no stdin/download/automatic cleanup or old overwrite.
# Learning when applicable: micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4j0Wc_stream_downstream_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4j0Wc_stream_downstream_cpu_"$run_stamp" --num 101 --note 'CPU newstream-v5 downstream namespace and no-teacher dispatch fixture. Observe prerequisite HOLD, final verdict, x/targets and raw quality separately. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4j0Wc_stream_downstream_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_gemma_stream_fork scripts.test_p106b_memory_stream scripts.test_p106b_gemma_mtp_resume
