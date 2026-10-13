#!/usr/bin/env bash
# Saved parent student only; diagnose parallel verification versus cache rebuild; no quality adoption
# Estimated 0.25h; no stdin/download/automatic cleanup or old overwrite.
# Learning (when applicable): micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/092_log_$(date +%Y%m%d)_P101A_Stage4bWb_parent_mtp_numeric_paths_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage4bWb_parent_mtp_numeric_paths_"$run_stamp" --num 092 --note 'Saved parent student only; diagnose parallel verification versus cache rebuild; no quality adoption. Read raw answers, x/assistant targets, final verdict and prerequisite status separately. STATIC_ONLY is not model quality or E2E. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage4bWb_parent_mtp_numeric_paths_"$run_stamp" --num 092 -- "$python_bin" -B -X utf8 scripts/diag_p101a_mtp_parity.py --arm parent_mtp --max-wall-sec 900 --execute
