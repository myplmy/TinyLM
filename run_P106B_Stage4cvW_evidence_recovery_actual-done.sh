#!/usr/bin/env bash
# Independent producer-owned evidence sufficiency/recovery; existing frozen work unchanged.
# CPU stages seconds/minutes; cost/train/evaluation bounds are explicit below.
# Only this stage's dependencies fail closed. No stdin, queue, installs or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cvW_evidence_recovery_actual_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cvW_evidence_recovery_actual_"$run_stamp" --num 101 --note 'Fixed parent and2finals,1024new counterfactual conversations plus retention. FP32 greedy64,actual/gold separate; free clarification semantic review remains offline. All shards below20MB, raw/weights private. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cvW_evidence_recovery_actual_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_recovery_evaluate.py --mode evaluate --max-wall-sec 3600 --execute
