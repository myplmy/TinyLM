#!/usr/bin/env bash
# Existing pinned public QA CPU inventory; no teacher/model/weights/GPU/download.
# Keep sealed evaluation/common-bpb/1024 budget and original source filters.
# Measure cap2 supply and hypothetical cap4, not a75M additive/adoption claim.
# CPU2, at most3600s total; do not overlap a GPU speed/cost experiment.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eqW_public_qa_supply_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eqW_public_qa_supply_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_public_qa_supply.py --mode prepare --max-wall-sec 3600 --execute
