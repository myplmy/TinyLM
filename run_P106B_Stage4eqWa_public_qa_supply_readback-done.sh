#!/usr/bin/env bash
# Immutable public QA inventory raw/source recount; no model/tokenizer/GPU.
# Fix only tuple-to-JSON-array wire metadata equality in an independent reader.
# Regression/preflight/execute; original collector/report/shards stay unchanged.
# Expected CPU2 under5min; completion is not75M quota/rights/semantic adoption.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eqWa_public_qa_supply_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=2 "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eqWa_public_qa_supply_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_public_qa_supply_readback.py --mode pipeline --execute
