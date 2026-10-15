#!/usr/bin/env bash
# V2 native runtime recovery, v1 data/CODE/raw immutable, no stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ceWb_interleave_root_readback_recovery_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ceWb_interleave_root_readback_recovery_"$run_stamp" --num 101 --note 'CPU raw paired recount by history/field, same-first-prefix, no model or truth promotion. Not75M/300M or world intelligence. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ceWb_interleave_root_readback_recovery_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_interleaved_evaluate_v2.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ceWb_interleave_root_readback_recovery_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_evaluate_v2.py --mode readback --execute
