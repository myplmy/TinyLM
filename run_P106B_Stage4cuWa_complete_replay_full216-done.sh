#!/usr/bin/env bash
# Independent producer-owned evidence sufficiency/recovery; existing frozen work unchanged.
# CPU stages seconds/minutes; cost/train/evaluation bounds are explicit below.
# Only this stage's dependencies fail closed. No stdin, queue, installs or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cuWa_complete_replay_full216_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cuWa_complete_replay_full216_"$run_stamp" --num 101 --note 'Two measured costs and whole deadline budget required. Additional4passes,216updates,micro8 accum16 cp-on. One final checkpoint. All shards below20MB, raw/weights private. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cuWa_complete_replay_full216_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_recovery_train.py --mode train --arm complete_replay --max-wall-sec 5400 --execute
