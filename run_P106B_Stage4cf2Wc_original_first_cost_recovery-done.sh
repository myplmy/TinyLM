#!/usr/bin/env bash
# Preserved V1 data; exact original producer validation; independent V2 outputs.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cf2Wc_original_first_cost_recovery_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf2Wc_original_first_cost_recovery_"$run_stamp" --num 101 --note 'Preserved original first QA course; cost8; checkpoint0. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cf2Wc_original_first_cost_recovery_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_original_qa3_train_v2.py --mode cost --arm first --execute --max-wall-sec 3600
