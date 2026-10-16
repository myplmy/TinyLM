#!/usr/bin/env bash
# CPU24 and actual fixed-source binding complete; no model inference.
# Same English MC only; frozen reference17 remains unchanged.
# CPU readback, no stdin/model load/new logits/training/downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eg0W_reference_extension_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eg0W_reference_extension_cpu_"$run_stamp" --num 101 --note 'CPU fixed new-scope labels only; no source reselection/model loading/logits. Same eligible English MC source IDs, not natural64 versus512 or cross-tokenizer CE. Old17 unavailable endpoints remain NOT_COMPLETE.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eg0W_reference_extension_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest -b scripts.test_p106b_night_reference_extension scripts.test_p106b_night_falcon_readback scripts.test_p106b_night_falcon_readback_controller
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eg0W_reference_extension_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_reference_extension.py --mode freeze --execute
