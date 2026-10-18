#!/usr/bin/env bash
# GATED exact CE4 full896; candidate-free1758 and separate4x4TF/native32
# New4query study; m8 accum16 seq1024 checkpointON; original A code untouched.
# Bounded CPU/GPU authority through Oct20 17:00 KST; no stdin/old overwrite.
# Estimated .3h; actual8cost gates and full raw readback own any adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4erZa_ce4_actual_answers_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4erZa_ce4_actual_answers_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_subject_role_entry.py --mode evaluate --endpoint ce --max-wall-sec 3600 --budget-hours 8 --execute
