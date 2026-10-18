#!/usr/bin/env bash
# GATED exact final640; same full8lanes and candidate-free actual answers; no training
# Bounded coordinator delegation through Oct20 17:00 KST; no stdin or old overwrite.
# Same m8 accum16 seq1024 checkpointON recipe; actual group WD must be preserved.
# Completion is technical evidence, never an intelligence/adoption verdict.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4epWc_cpt_unique32k_final_eval_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4epWc_cpt_unique32k_final_eval_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_cpt_unique32k_entry.py --mode eval_final --execute
