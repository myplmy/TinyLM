#!/usr/bin/env bash
# Fixed9/13; shared and per-target response/EOT value fields,40 auxiliary steps.
# About3-10min,4GiB free. No body optimizer, generated answers or checkpoint.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_target_values check; fi
"$python_bin" -B -m scripts.diag_p108b_target_values check || exit $?
extra=()
if [[ "${1:-}" == --resume ]]; then extra=(--resume); fi
timeout --signal=TERM --kill-after=20s 1260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage34Wb_target_window_values --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_target_values actual "${extra[@]}"
exit $?
