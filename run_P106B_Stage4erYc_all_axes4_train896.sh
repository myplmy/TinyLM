#!/usr/bin/env bash
# GATED all3cost8; same4queries/native/order; fresh parent all3 negatives896
# New4query study; m8 accum16 seq1024 checkpointON; original A code untouched.
# Bounded CPU/GPU authority through Oct20 17:00 KST; no stdin/old overwrite.
# Estimated 1.3h; actual8cost gates and full raw readback own any adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4erYc_all_axes4_train896_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4erYc_all_axes4_train896_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_subject_role_entry.py --mode train --arm all_axes --max-wall-sec 7200 --budget-hours 8 --execute
