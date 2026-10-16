#!/usr/bin/env bash
# Completed 2026-10-16 12:48:06 KST; raw124756 exit0, CPU24 before any new GPU.
# Independent producer-owned evidence sufficiency/recovery; existing frozen work unchanged.
# CPU stages seconds/minutes; cost/train/evaluation bounds are explicit below.
# Only this stage's dependencies fail closed. No stdin, queue, installs or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cs0W_evidence_recovery_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs0W_evidence_recovery_cpu_"$run_stamp" --num 101 --note 'CPU24 for dependency omission, counterfactual queries, all-positive masks, fixed parent module and paired traces. No model forward or CUDA. All shards below20MB, raw/weights private. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs0W_evidence_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_recovery.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs0W_evidence_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_recovery_course.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs0W_evidence_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_recovery_train.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs0W_evidence_recovery_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_evidence_recovery_evaluation.py
