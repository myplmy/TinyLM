#!/usr/bin/env bash
# GATED original A exact CE768/990/raw; CE256 new CF first answers, paired original view0 reuse
# Same frozen A model/data; only queried role values change in evaluation.
# Estimated .3h; bounded3600s per GPU endpoint; no stdin or old overwrite.
# Completion is technical evidence, never an intelligence/adoption verdict.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4eoWb_cf_ce_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4eoWb_cf_ce_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_relation_cf_entry.py --mode evaluate --model ce --max-wall-sec 3600 --execute
