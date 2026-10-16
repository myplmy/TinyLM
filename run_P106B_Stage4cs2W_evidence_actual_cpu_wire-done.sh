#!/usr/bin/env bash
# Completed 2026-10-16 12:53:43 KST; raw125308 exit0, actual7E CPU body/consumers match.
# Independent producer-owned evidence sufficiency/recovery; existing frozen work unchanged.
# CPU stages seconds/minutes; cost/train/evaluation bounds are explicit below.
# Only this stage's dependencies fail closed. No stdin, queue, installs or cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4cs2W_evidence_actual_cpu_wire_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Preserve old raw evidence; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs2W_evidence_actual_cpu_wire_"$run_stamp" --num 101 --note 'Load read-only parent7E and verify actual entire encoder/binary/native consumers. No forward, CUDA, optimizer or checkpoint. All shards below20MB, raw/weights private. Full smoke remains user-owned NOT_RUN.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4cs2W_evidence_actual_cpu_wire_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_evidence_recovery_train.py --mode wire --execute
