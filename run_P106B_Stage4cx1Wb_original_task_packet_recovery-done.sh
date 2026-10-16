#!/usr/bin/env bash
# Original task direction recovery; previous CPU/raw error remain immutable.
# CPU seconds/minutes, no teacher/model GPU in this stage.
# Failed dependencies stop only this stage. No stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cx1Wb_original_task_packet_recovery_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cx1Wb_original_task_packet_recovery_"$run_stamp" --num 101 --note 'Correct actual renderer reference metadata. Freeze only previously absent namespace, exact8 sources preserved. No model. Original data/weights unchanged; full smoke user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cx1Wb_original_task_packet_recovery_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_task_contract.py --mode freeze --execute
