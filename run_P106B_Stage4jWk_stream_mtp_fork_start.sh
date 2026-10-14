#!/usr/bin/env bash
# User-run newstream-v5 first1h window; baseline V3 semantics UNVERIFIED, not visible-source adoption
# No stdin/download/old mutation; no automatic quality or new prompt adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4jWk_stream_mtp_fork_start_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve existing raw; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4jWk_stream_mtp_fork_start_"$run_stamp" --num 101 --note 'User-run newstream-v5 first1h window; baseline V3 semantics UNVERIFIED, not visible-source adoption. Dataset source-visible gaps remain separate; read raw/actualx/pause/resource evidence. This is preparation; GPT production execution NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4jWk_stream_mtp_fork_start_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_stream_fork.py --mode start --max-wall-sec 3600 --execute
