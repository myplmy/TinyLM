#!/usr/bin/env bash
# Saved new128-update endpoint on same32 development cases; old128 first answers inherited by SHA. [Completed; command/SHA in WIP_20261014b_LOOKUP_LAUNCHER_ARCHIVE.]
# No training/checkpoint write. Approx0.05h/cap600s; same FP32math/cache/nativeK1/greedy64.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4abW_binding_transfer_after_train_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4abW_binding_transfer_after_train_"$stamp" --num 101 --note 'Same32 authored lookup development cases, not independent general intelligence test. Actual newstudent answers; old128 prior report pinned by SHA. Diagnostic names never in train/val. No training/teacher/weight save.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4abW_binding_transfer_after_train_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_followup.py --execute --max-wall-sec 600
