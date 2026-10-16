#!/usr/bin/env bash
# Completed 2026-10-16 15:20:50 KST; raw152045 exit0, all raw/pairs recounted.
# Known sufficiency preference: beta0 versus0.1, same replay and16 pairs/update.
# CPU seconds or measured GPU minutes; model operations bounded explicitly.
# Failed prerequisites stop only this stage. No stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4deW_evidence_preference_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4deW_evidence_preference_readback_"$run_stamp" --num 101 --note 'All evidence/role/source/fiction raw counts and same-neutral pairs recounted. Free clarification proxy not semantic truth. Fresh namespace only, old raw/weights unchanged. Private shards below20MB. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4deW_evidence_preference_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_preference_evaluate.py --mode readback --execute
