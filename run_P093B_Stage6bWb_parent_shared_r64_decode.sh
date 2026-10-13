#!/usr/bin/env bash
# Same saved parents/factors; fresh24 cache-off guards; no training or checkpoint write
# Estimated 0.25h; no stdin/download/automatic cleanup or old overwrite.
# Learning (when applicable): micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/103_log_$(date +%Y%m%d)_P093B_Stage6bWb_parent_shared_r64_decode_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6bWb_parent_shared_r64_decode_"$run_stamp" --num 103 --note 'Same saved parents/factors; fresh24 cache-off guards; no training or checkpoint write. Read raw answers, x/assistant targets, final verdict and prerequisite status separately. STATIC_ONLY is not model quality or E2E. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P093B_Stage6bWb_parent_shared_r64_decode_"$run_stamp" --num 103 -- "$python_bin" -B -X utf8 scripts/diag_p093b_generation_attribution.py --mode decode --tag p093b_generation_v2_s1337 --max-wall-sec 900 --execute
