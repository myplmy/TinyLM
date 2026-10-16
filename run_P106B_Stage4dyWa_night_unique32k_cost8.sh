#!/usr/bin/env bash
# One-time authorized overnight local source contrast; original assets read-only.
# No stdin, teacher calls, downloads or product-default changes;09:00 GPU stop.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dyWa_night_unique32k_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dyWa_night_unique32k_cost8_"$run_stamp" --num 101 --note 'Same originalP090B actual8 QA updates for new32k once; no checkpoint writes; final640 primary, DEV representative separate, same processed rows are not same unique information or exact token match.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dyWa_night_unique32k_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_diversity.py --mode cost --max-wall-sec 14400 --execute
