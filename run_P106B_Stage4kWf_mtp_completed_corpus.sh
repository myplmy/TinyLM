#!/usr/bin/env bash
# Only when cumulative unique train75M and language/task/val/source quotas complete; CPU merge
# Estimated 0.5h; no stdin/download/automatic cleanup or old overwrite.
# Learning (when applicable): micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4kWf_mtp_completed_corpus_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4kWf_mtp_completed_corpus_"$run_stamp" --num 101 --note 'Only when cumulative unique train75M and language/task/val/source quotas complete; CPU merge. Read raw answers, x/assistant targets, final verdict and prerequisite status separately. STATIC_ONLY is not model quality or E2E. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4kWf_mtp_completed_corpus_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_mtp_resume.py --mode finalize --execute
