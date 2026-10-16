#!/usr/bin/env bash
# Completed CPU attempt: strict loading succeeded, metadata serialization failed.
# One-time authorized overnight reference; original assets are read-only.
# No installs/downloads/stdin or checkpoint writes;09:00 GPU stop.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dw0W_night_falcon_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dw0W_night_falcon_cpu_"$run_stamp" --num 101 --note 'CPU9 and actual strictly loaded local Falcon asset/tokenization/frozen896; offline no model forward; not architecture-only causality or a broad intelligence certificate.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dw0W_night_falcon_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_falcon
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dw0W_night_falcon_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_falcon.py --mode freeze --max-wall-sec 900 --execute
