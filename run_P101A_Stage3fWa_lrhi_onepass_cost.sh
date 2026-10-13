#!/usr/bin/env bash
# Fresh frozen8M parentNTP cost32; Adam1e-4 Muon4e-4; not quality gate
# Estimated 0.15h; no stdin/download/automatic cleanup or old overwrite.
# Learning (when applicable): micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/092_log_$(date +%Y%m%d)_P101A_Stage3fWa_lrhi_onepass_cost_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3fWa_lrhi_onepass_cost_"$run_stamp" --num 092 --note 'Fresh frozen8M parentNTP cost32; Adam1e-4 Muon4e-4; not quality gate. Read raw answers, x/assistant targets, final verdict and prerequisite status separately. STATIC_ONLY is not model quality or E2E. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3fWa_lrhi_onepass_cost_"$run_stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/diag_p101a_lr_retention.py --mode calibrate --lr-scale 1.0 --max-wall-sec 1200 --execute
