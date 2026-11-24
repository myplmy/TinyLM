#!/usr/bin/env bash
# Paired ORIGINAL-centred total preservation, SAME4 and ADAPT_R4.
# About5-20min,4GiB free. Compare all other axes to Stage26Wf; no training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_regularizer check; fi
"$python_bin" -B -m scripts.diag_p108b_regularizer check || exit $?
timeout --signal=TERM --kill-after=20s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage26Wg_regularizer_total --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_regularizer actual --mode total
exit $?
