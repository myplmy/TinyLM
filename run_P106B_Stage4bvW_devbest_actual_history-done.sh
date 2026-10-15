#!/usr/bin/env bash
# Completed prelocked DEV2/2 reading, raw031822 exit0; no training or new weights.
# Deadline Oct16 17:00 KST,45minute closure margin. No stdin or global queue.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bvW_devbest_actual_history_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bvW_devbest_actual_history_"$run_stamp" --num 101 --note 'Regression6 then prelocked DEV epoch2 candidates. Same source mixed/repeated controls plus retention; final4epoch stays primary. No TEST-best selection or training/checkpoint. Full user smoke NOT_RUN; pseudo targets are not world truth.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bvW_devbest_actual_history_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_dualqa_dialogue_controls.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bvW_devbest_actual_history_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_followup.py --mode devbest --execute --max-wall-sec 10800
