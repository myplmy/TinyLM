#!/usr/bin/env bash
# Matched new-solver incremental-preservation control, SAME4 and ADAPT_R4.
# About5-20min,4GiB free. Same controller; no training/value fitting/CP writes.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_regularizer check; fi
"$python_bin" -B -m scripts.diag_p108b_regularizer check || exit $?
timeout --signal=TERM --kill-after=20s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage26Wf_regularizer_incremental --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_regularizer actual --mode incremental
exit $?
