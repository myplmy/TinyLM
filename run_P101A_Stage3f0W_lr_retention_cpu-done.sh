#!/usr/bin/env bash
# CPU one-pass exposure and joint Adam/Muon scale regression
# Estimated 0.02h; no stdin/download/automatic cleanup or old overwrite.
# Learning (when applicable): micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/092_log_$(date +%Y%m%d)_P101A_Stage3f0W_lr_retention_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3f0W_lr_retention_cpu_"$run_stamp" --num 092 --note 'CPU one-pass exposure and joint Adam/Muon scale regression. Read raw answers, x/assistant targets, final verdict and prerequisite status separately. STATIC_ONLY is not model quality or E2E. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P101A_Stage3f0W_lr_retention_cpu_"$run_stamp" --num 092 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p101a_lr_retention scripts.test_p101a_sft_mtp_driver
