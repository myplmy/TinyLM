#!/usr/bin/env bash
# Completed 2026-10-16 12:50:02 KST; raw124904 exit0, matched course/newtest frozen.
# Independent producer-owned evidence sufficiency/recovery; existing frozen work unchanged.
# CPU stages seconds/minutes; cost/train/evaluation bounds are explicit below.
# Only this stage's dependencies fail closed. No stdin, queue, installs or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cs1W_evidence_recovery_course_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs1W_evidence_recovery_course_"$run_stamp" --num 101 --note 'Freeze matched6912-row curricula and new128neutral four-cell test. Existing raw-source64 is posthoc/partly invalid pure QA only. All shards below20MB, raw/weights private. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs1W_evidence_recovery_course_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_recovery_course.py --execute
