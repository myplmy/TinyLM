#!/usr/bin/env bash
# P106B_Stage4fdWa_legacy_native_prefix_pilot: CPU-only legacy TRAIN to canonical chat32 bounded preparation.
# Source is stat/small config only; pilot reads prefix1048576 IDs and current VAL3005000 IDs.
# No model/GPU, old-cache mutation, download, full-build opt-in, raw-text Git, or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fdWa_legacy_native_prefix_pilot_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fdWa_legacy_native_prefix_pilot_"$run_stamp" --num 101 --note 'CPU regression and exact metadata/codec lineage are prerequisites. Source reads bin stat only. Pilot reads old TRAIN first1048576 uint16 IDs plus complete current VAL3005000 IDs, not legacy VAL. Preserve exact bytes, incomplete-tail exclusion and current VAL full/partial exclusions. This stage cap1200s GPU=N. No full build, model, training or new-knowledge claim; larger pool is not additional dialogue tokens.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fdWa_legacy_native_prefix_pilot_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_expansion.py --mode pilot --max-wall-sec 1200 --execute

