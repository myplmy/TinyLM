#!/usr/bin/env bash
# Completed once; immutable commands are archived before cleanup.
# Immutable original inputs; row-occurrence keys repair aggregation only.
# CPU only, about .05h; no training/checkpoint writes or stdin.
# Authority ends2026-10-17 10:00KST;09:00 GPU stop; original raw preserved.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dnWb_night_recovery_paired_readback_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dnWb_night_recovery_paired_readback_"$run_stamp" --num 101 --note 'Same original scientific inputs and generation. Row occurrence keys, exact source/raw SHA and full lane receipts; historical failure preserved. Carried parent answers are not regenerated; missing lanes only. Scores are not broad intelligence or semantic truth certification.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dnWb_night_recovery_paired_readback_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_eval_recovery.py --mode readback --max-wall-sec 7200 --execute
