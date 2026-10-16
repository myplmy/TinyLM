#!/usr/bin/env bash
# Closed actual execution; exact scope/raw result preserved, not global quality PASS.
# Same English MC; explicit completed upstream parent readback before this retry.
# CPU readback, no stdin/model load/new logits/training/downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4egWb_reference_extension_after_parent_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4egWb_reference_extension_after_parent_"$run_stamp" --num 101 --note 'Existing Falcon896/raw17 plus new unique2 full and parent64 two completed readbacks required. CPU raw/source/body/checkpoint-path recount and common English MC comparison; same-checkpoint endpoint labels grouped, no old gate completion.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4egWb_reference_extension_after_parent_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_reference_extension.py --mode readback --execute
