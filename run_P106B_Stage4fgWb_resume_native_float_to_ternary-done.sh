#!/usr/bin/env bash
# COMPLETE: raw verdict0 and result101 section365 recorded; preserve commands, no automatic rerun.
# P106B_Stage4fgWb_resume_native_float_to_ternary: new private cross provenance; same frozen evaluation computation.
# Original native training, resume SFT training and resume four diagonals are distinct providers.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fgWb_resume_native_float_to_ternary_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fgWb_resume_native_float_to_ternary_"$run_stamp" --num 101 --note 'Cross resume21KST: exact original native CP and resume SFT CP; four resume diagonal evaluations must be complete. Strict CPU training-route load, context closed before CUDA, explicit other inference route. No learning/checkpoint write/retag/generic float loader. Same ordered1694/FP32-MATH/greedy64/KV-on/MTP-off; family8400 record600, worker cap1800s. Four new6776 answers stay distinct from reused6776. Technical completion is not semantic quality; files below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fgWb_resume_native_float_to_ternary_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_route_cross_resume.py --mode evaluate --trained-mode float --inference-mode ternary --endpoint native --max-wall-sec 1800 --execute
