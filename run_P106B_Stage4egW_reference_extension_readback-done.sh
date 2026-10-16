#!/usr/bin/env bash
# Closed9: manually dispatched before the upstream CPU readback had finished.
# Same English MC only; frozen reference17 remains unchanged.
# CPU readback, no stdin/model load/new logits/training/downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4egW_reference_extension_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4egW_reference_extension_readback_"$run_stamp" --num 101 --note 'Existing Falcon896/raw17 plus new unique2 full and parent64 two completed readbacks required. CPU raw/source/body/checkpoint-path recount and common English MC comparison; same-checkpoint endpoint labels grouped, no old gate completion.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4egW_reference_extension_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_reference_extension.py --mode readback --execute
