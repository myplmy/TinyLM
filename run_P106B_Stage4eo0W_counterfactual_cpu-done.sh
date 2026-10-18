#!/usr/bin/env bash
# CPU44 plus real tokenizer/source freeze; evaluation-only256, no learned model/GPU; originalA data preserved
# Same frozen A model/data; only queried role values change in evaluation.
# Estimated .1h; bounded3600s per GPU endpoint; no stdin or old overwrite.
# Completion is technical evidence, never an intelligence/adoption verdict.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export CUDA_VISIBLE_DEVICES=""
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eo0W_counterfactual_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eo0W_counterfactual_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_relation_cf_entry.py --mode prepare --max-wall-sec 3600 --execute
