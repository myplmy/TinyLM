#!/usr/bin/env bash
# Broad course checkpoints on old24 development prompts, not an independent test.
# No stdin/download/training/old mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4tWd_broad_transfer_dev_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve raw; new stage/tag required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4tWd_broad_transfer_dev_"$run_stamp" --num 101 --note 'Broad saved parent/two students: old24 repeated development prompts, not an independent test. All raw answers retained; free semantics judged offline. GPT direct run only before 2026-10-14 17:00 KST.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4tWd_broad_transfer_dev_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_context_transfer.py --broad --execute --max-wall-sec 600
