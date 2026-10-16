#!/usr/bin/env bash
# Completed once; archive exact commands and source before cleanup.
# New v2 namespace preserves the failed v1 CPU raw and partial896 source.
# CPU only; no forward, GPU, installation, download or weight writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dw0Wb_night_falcon_cpu_json_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dw0Wb_night_falcon_cpu_json_"$run_stamp" --num 101 --note 'CPU12 plus actual strictly loaded offline Falcon; stable JSON loading proof in new v2 namespace, old error preserved. No forward/GPU/weight writes.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dw0Wb_night_falcon_cpu_json_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_night_falcon
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dw0Wb_night_falcon_cpu_json_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_falcon.py --mode freeze --max-wall-sec 900 --execute
