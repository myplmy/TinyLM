#!/usr/bin/env bash
# Completed once; archive exact commands and source before cleanup.
# One-time authorized overnight local source contrast; original assets read-only.
# No stdin, teacher calls, downloads or product-default changes;09:00 GPU stop.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dy0W_night_diversity_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dy0W_night_diversity_cpu_"$run_stamp" --num 101 --note 'CPU18 plus actual32k source/quarter0 exact encoder and unchanged DEVTEST; no forward/GPU; final640 primary, DEV representative separate, same processed rows are not same unique information or exact token match.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dy0W_night_diversity_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_diversity_data scripts.test_p106b_night_diversity
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dy0W_night_diversity_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_diversity.py --mode freeze --max-wall-sec 900 --execute
