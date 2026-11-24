#!/usr/bin/env bash
# Same Tiny14 directions, held-out step sizes and local curvature prediction.
# No optimization or generated answers. Existing full-step effects are reused.
# About3-12min,4GiB free; fail closed before source/CPU admission.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_prediction_scale check; fi
"$python_bin" -B -m scripts.diag_p108b_prediction_scale check || exit $?
timeout --signal=TERM --kill-after=20s 1260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage33Wb_tiny_step_prediction --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_prediction_scale actual --arm tiny
exit $?
