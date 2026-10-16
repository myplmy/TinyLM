#!/usr/bin/env bash
# Posthoc fixed-history source-only intervention; primary/model/data unchanged.
# Dependencies fail closed; no stdin, downloads, queue calls or old output reset.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ckW_fixed_history_source_windows_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve original raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ckW_fixed_history_source_windows_"$run_stamp" --num 101 --note 'Same parent/threeQA models, FULL384 must reproduce primary first; fixed history and source-only interventions. GPU bound30min, no training/CPT. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ckW_fixed_history_source_windows_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_window.py --mode probe --execute --max-wall-sec 1800
