#!/usr/bin/env bash
# Completed CPU6/joint raw recheck, raw034933 exit0; same fixed8source packet.
# Deadline Oct16 17:00 KST,45minute closure margin. No stdin or global queue.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4bwWb_controlled_dialogue_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bwWb_controlled_dialogue_readback_"$run_stamp" --num 101 --note 'CPU raw readback after both followup reports. Same document-root pairing, actual versus gold history and legitimate repetition separated. Fixed8source packet, no automatic semantic grade/models/training. Full user smoke NOT_RUN; pseudo targets are not world truth.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bwWb_controlled_dialogue_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_dualqa_dialogue_controls.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4bwWb_controlled_dialogue_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_dualqa_followup.py --mode readback --execute
