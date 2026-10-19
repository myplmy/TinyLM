#!/usr/bin/env bash
# P106B_Stage4exWb_span_readout_recount: saved-head extractive readout, not general generation adoption.
# No training, checkpoint write, download, input prompt, or old asset mutation.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4exWb_span_readout_recount_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4exWb_span_readout_recount_"$run_stamp" --num 101 --note 'Regression then exact source/CP prerequisite then execution and final receipt. Same trained backbone; vocabulary versus two extractive span policies. No truth verifier or new training. Estimated.2h GPU=N, worker cap600s.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4exWb_span_readout_recount_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_span_readout.py --mode readback --max-wall-sec 600 --execute
