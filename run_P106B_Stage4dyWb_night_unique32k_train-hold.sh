#!/usr/bin/env bash
# HOLD20261017: original budget scope unchanged; separate scope_v2, never completed by proxy.
# One-time authorized overnight local source contrast; original assets read-only.
# No stdin, teacher calls, downloads or product-default changes;09:00 GPU stop.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dyWb_night_unique32k_train_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dyWb_night_unique32k_train_"$run_stamp" --num 101 --note 'Unique32k once across four logical quarters/640 matched updates, not32k repeated4epochs; full budget09:00; final640 primary, DEV representative separate, same processed rows are not same unique information or exact token match.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dyWb_night_unique32k_train_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_diversity.py --mode train --max-wall-sec 14400 --execute
