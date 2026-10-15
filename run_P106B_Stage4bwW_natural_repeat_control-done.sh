#!/usr/bin/env bash
# Completed repeat control3endpoints, raw025851 exit0; no training/checkpoint.
# Deadline Oct16 17:00 KST,45minute closure margin. No stdin or global queue.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bwW_natural_repeat_control_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bwW_natural_repeat_control_"$run_stamp" --num 101 --note 'Regression6 then primary/lock prerequisites then actual repeated-question inference. Identical legitimate answers allowed; actual first errors retained. Copy rate is not correctness. No training/checkpoint. Full user smoke NOT_RUN; pseudo targets are not world truth.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bwW_natural_repeat_control_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_dualqa_dialogue_controls.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bwW_natural_repeat_control_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_followup.py --mode repeat --execute --max-wall-sec 7200
