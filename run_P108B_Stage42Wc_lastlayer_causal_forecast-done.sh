#!/usr/bin/env bash
# Last-layer-only native/analytic forecast and temporary output restoration.
# Reused DEV96 and old protected7 only. No FINAL answers, fit or optimizer.
# Estimate1-5min;10min bound;one GPU. Source failure stops this diagnostic.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_lastlayer_forecast check
fi
"$python_bin" -B -m scripts.diag_p108b_lastlayer_forecast check || exit $?
timeout --signal=TERM --kill-after=20s 720s "$python_bin" -B scripts/runlog.py --num 108 --name P108B_Stage42Wc_lastlayer_causal_forecast -- "$python_bin" -B -u -m scripts.diag_p108b_lastlayer_forecast actual
exit $?
