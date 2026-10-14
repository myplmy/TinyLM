#!/usr/bin/env bash
# Newstream-v5 completed corpus only; teacher down before two student updates
# Estimated 0.5h; no stdin/download/automatic cleanup or old overwrite.
# Learning when applicable: micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4k0Wg_stream_student_wire_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4k0Wg_stream_student_wire_"$run_stamp" --num 101 --note 'Newstream-v5 completed corpus only; teacher down before two student updates. Observe prerequisite HOLD, final verdict, x/targets and raw quality separately. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4k0Wg_stream_student_wire_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_stream_fork.py --mode wire --execute
