#!/usr/bin/env bash
# DEV-frozen one global edit versus original on128 new inputs/144 actual turns.
# Same greedy128/FP32 route. No fit, selection, optimizer or checkpoint writes.
# Estimate5-15min;30min bounded. A failed source admission stops this trial.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_pm_evaluate check
fi
"$python_bin" -B -m scripts.diag_p108b_pm_evaluate check || exit $?
timeout --signal=TERM --kill-after=20s 1920s "$python_bin" -B scripts/runlog.py --num 108 --name P108B_Stage41Wc_frozen_fresh_language -- "$python_bin" -B -u -m scripts.diag_p108b_pm_evaluate generate
exit $?
