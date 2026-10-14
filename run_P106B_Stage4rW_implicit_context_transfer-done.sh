#!/usr/bin/env bash
# Same saved parent/three students:96 independent first answers; no training
# Do not train on this test; no stdin/download/old mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4rW_implicit_context_transfer_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4rW_implicit_context_transfer_"$run_stamp" --num 101 --note 'Same saved parent/three students:96 independent first answers; no training. Code/reference agreement and free clarification review are separate; no broad intelligence claim. GPT run authorized only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4rW_implicit_context_transfer_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_context_transfer.py --execute --max-wall-sec 600
