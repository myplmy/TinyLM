#!/usr/bin/env bash
# CPU fresh6-ancestor namespace/stream boundaries; generation baseline unchanged
# No stdin/download/old mutation; no automatic quality or new prompt adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4j0Wb_stream_fork_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve existing raw; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4j0Wb_stream_fork_cpu_"$run_stamp" --num 101 --note 'CPU fresh6-ancestor namespace/stream boundaries; generation baseline unchanged. Dataset source-visible gaps remain separate; read raw/actualx/pause/resource evidence. This is preparation; GPT production execution NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4j0Wb_stream_fork_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_gemma_stream_fork scripts.test_p106b_memory_stream
