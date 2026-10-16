#!/usr/bin/env bash
# Independent content-repair dataset, original sources/old producers unchanged.
# Dependencies fail closed; no stdin, install, downloads, queue or cleanup calls.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cm1W_gemma_repair3_pilot16_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cm1W_gemma_repair3_pilot16_"$run_stamp" --num 101 --note 'Gemma4 MTP on, repair original TRAIN16 only, three content QA labels, native reasoning preserved outside student. Structural wire/cost gate, not truth PASS. All raw/canonical shards below20MB. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cm1W_gemma_repair3_pilot16_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_repair3.py --mode pilot --execute --max-wall-sec 900
