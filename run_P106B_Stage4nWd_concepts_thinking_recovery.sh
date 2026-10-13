#!/usr/bin/env bash
# Only after current16K capacity; MTP OFF factorial concepts1/2/4 and thinking256/1024
# Estimated 0.75h; no stdin/download/automatic cleanup or old overwrite.
# Learning (when applicable): micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4nWd_concepts_thinking_recovery_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4nWd_concepts_thinking_recovery_"$run_stamp" --num 101 --note 'Only after current16K capacity; MTP OFF factorial concepts1/2/4 and thinking256/1024. Read raw answers, x/assistant targets, final verdict and prerequisite status separately. STATIC_ONLY is not model quality or E2E. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4nWd_concepts_thinking_recovery_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_ac.py --mode panel --tag p106b_gemma_ac_v2_s1337 --max-wall-sec 3600 --execute
