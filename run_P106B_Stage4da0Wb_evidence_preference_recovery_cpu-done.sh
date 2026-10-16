#!/usr/bin/env bash
# Known sufficiency preference: beta0 versus0.1, same replay and16 pairs/update.
# CPU seconds or measured GPU minutes; model operations bounded explicitly.
# Failed prerequisites stop only this stage. No stdin, queue or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4da0Wb_evidence_preference_recovery_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4da0Wb_evidence_preference_recovery_cpu_"$run_stamp" --num 101 --note 'CPU21 known evidence preferences, visible input aliases, actual masks, zero-beta math, loader ownership. No CUDA/forward. Fresh namespace only, old raw/weights unchanged. Private shards below20MB. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4da0Wb_evidence_preference_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_preference.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4da0Wb_evidence_preference_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_preference_course.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4da0Wb_evidence_preference_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_preference_train.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4da0Wb_evidence_preference_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_preference_evaluation.py
