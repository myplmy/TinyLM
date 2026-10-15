#!/usr/bin/env bash
# New interleaved relation schedule; no old data/CODE/CPT overwrite or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cb2W_interleave_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; new stage required.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb2W_interleave_cost8_"$run_stamp" --num 101 --note 'New interleaved fact1 cost8 only, exact same mathematical training functions and parent. Checkpoint0. Not75M/300M or world intelligence. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cb2W_interleave_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_relation_interleaved_train.py --mode cost --arm fact1 --execute --max-wall-sec 3600
