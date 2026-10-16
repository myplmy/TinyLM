#!/usr/bin/env bash
# Completed 2026-10-16 10:52:28 KST; raw100716 exit0, accepted ko256/en256.
# Independent content-repair dataset, original sources/old producers unchanged.
# Dependencies fail closed; no stdin, install, downloads, queue or cleanup calls.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cm2W_gemma_repair3_source512_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cm2W_gemma_repair3_source512_"$run_stamp" --num 101 --note 'Explicit sealed continuation after pilot: common512 accepted sources, ko/en256 each, shared3 structural attempts, no root restart, no student training. All raw/canonical shards below20MB. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cm2W_gemma_repair3_source512_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_repair3.py --mode produce --execute --max-wall-sec 5400
