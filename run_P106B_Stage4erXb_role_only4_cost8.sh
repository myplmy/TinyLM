#!/usr/bin/env bash
# GATED CPU freeze; role-only4 cost8 same full16 computation, no checkpoint
# New4query study; m8 accum16 seq1024 checkpointON; original A code untouched.
# Bounded CPU/GPU authority through Oct20 17:00 KST; no stdin/old overwrite.
# Estimated .25h; actual8cost gates and full raw readback own any adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4erXb_role_only4_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4erXb_role_only4_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_subject_role_entry.py --mode cost --arm role_only --max-wall-sec 1800 --budget-hours 8 --execute
