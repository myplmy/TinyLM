#!/usr/bin/env bash
# Same-information curriculum-order test, no stdin or old output overwrite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ceW_interleave_root_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ceW_interleave_root_readback_"$run_stamp" --num 101 --note 'CPU only: verify raw answers and paired roots by history/field; not world truth or TEST model selection. Not75M/300M or general intelligence. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ceW_interleave_root_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_relation_interleaved_evaluate.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ceW_interleave_root_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_evaluate.py --mode readback --execute
