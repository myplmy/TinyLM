#!/usr/bin/env bash
# Known sufficiency preference: beta0 versus0.1, same replay and16 pairs/update.
# CPU seconds or measured GPU minutes; model operations bounded explicitly.
# Failed prerequisites stop only this stage. No stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dbWb_orpo_preference_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dbWb_orpo_preference_cost8_"$run_stamp" --num 101 --note 'Measured cost8 beta0.1, same model/data/pair compute. No checkpoint. Fresh namespace only, old raw/weights unchanged. Private shards below20MB. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dbWb_orpo_preference_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_preference_train.py --mode cost --arm orpo010 --max-wall-sec 1800 --execute
