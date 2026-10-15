#!/usr/bin/env bash
# Original-QA curriculum, immutable input/new outputs, no stdin or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cf1W_original_role_matched_corpus_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf1W_original_role_matched_corpus_"$run_stamp" --num 101 --note 'Original2004 source TRAIN, same code4096/fiction256 replay, first versus three QA. Reserved64 remains evaluation-only. New1600 indexed native windows; no cache copies. No world-truth certification. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf1W_original_role_matched_corpus_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_original_qa3_course.py --execute
