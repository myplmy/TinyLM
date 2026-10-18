#!/usr/bin/env bash
# GATED A990x3/raw; old contrast2x4 TF, source/body binding, no training
# New4query study; m8 accum16 seq1024 checkpointON; original A code untouched.
# Bounded CPU/GPU authority through Oct20 17:00 KST; no stdin/old overwrite.
# Estimated .15h; actual8cost gates and full raw readback own any adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4erWb_old_contrast_four_candidates_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4erWb_old_contrast_four_candidates_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_subject_role_entry.py --mode probe_old --model contrast --max-wall-sec 1800 --budget-hours 8 --execute
