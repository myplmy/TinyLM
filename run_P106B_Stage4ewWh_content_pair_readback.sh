#!/usr/bin/env bash
# P106B Stage4ewWh: same frozen course; token/content weights only.
# Explicit m8 a16 seq1024 ckptON; fixed parent; old assets remain unchanged.
# No stdin, download, W&B upload, or automatic quality/adoption claim.
# Cost callers must ensure five minutes GPU idle and stop heavy CPU work.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ewWh_content_pair_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a distinct experiment stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ewWh_content_pair_readback_"$run_stamp" --num 101 --note 'Read regression, prerequisite and final receipt before judging. Paired content objective study; actual answers, EOT/content losses and native retention are separate. Technical completion is not intelligence. Estimated 0.2 hours; GPU=N; per-worker cap 600 seconds. Independent arms preserve failed evidence.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ewWh_content_pair_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_content_recovery.py --mode readback --max-wall-sec 600 --execute
