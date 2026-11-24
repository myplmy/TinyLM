#!/usr/bin/env bash
# Same full14 numerical canary with existing strict cuBLAS cleanup.
# About2min,4GiB free; preserve v1 cleanup-negative report and original CP.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -c 'from scripts.diag_p108b_value_library import verify; verify(); print("[CHECK_ONLY] v2 source/profile/authority verified; GPU NOT_RUN")'
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage23Wb_full14_canary --num 108 --note 'Nov16 directive140. V1 full14 parity/gradient succeeded but ordinary CUDA cleanup retained workspace17,039,360B; next entry guard stopped before value updates. V2 reuses existing strict allocator/cuBLAS cleaner and keeps zero-byte threshold. Same completed model, targets and FP32Math. Read14-layer/core plus cleanup proof; technical only.'
timeout --signal=TERM --kill-after=20s 900s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage23Wb_full14_canary --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_value_library canary
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage23Wb_full14_canary --num 108 --note "Final v2 canary exit=$result; parity/gradient/core/CUDA are separate from model quality."
exit "$result"
