#!/usr/bin/env bash
# Reuse completed14x24 predictions and outcomes;no new model or GPU.
# Hold out both semantic concept and layer from calibration fitting.
# Retrospective predictor audit,not an unseen edit/quality validation.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_forecast_cv check
fi
"$python_bin" -B -m scripts.diag_p108b_forecast_cv check || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage50Wa_forecast_cv_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_forecast_cv actual
exit $?
