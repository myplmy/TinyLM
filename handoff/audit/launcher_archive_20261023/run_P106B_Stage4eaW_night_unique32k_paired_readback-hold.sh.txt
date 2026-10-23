#!/usr/bin/env bash
# HOLD20261017: original budget scope unchanged; separate scope_v2, never completed by proxy.
# Same immutable scientific inputs; unique32k once versus8k four-pass baseline.
# No stdin, training, checkpoint writes, installs or downloads;09:00 GPU stop.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eaW_night_unique32k_paired_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eaW_night_unique32k_paired_readback_"$run_stamp" --num 101 --note 'Raw original/history/body/receipt recount and paired8kfourpass versus32konce comparison; repeated development cohort, no broad intelligence certificate.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eaW_night_unique32k_paired_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_diversity_eval.py --mode readback --max-wall-sec 7200 --execute
