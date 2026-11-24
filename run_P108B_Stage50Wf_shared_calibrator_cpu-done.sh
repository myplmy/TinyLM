#!/usr/bin/env bash
# Same held-fact calibrator for every ranked layer; native/model/GPU zero.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_forecast_common check
fi
"$python_bin" -B -m scripts.diag_p108b_forecast_common check || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage50Wf_shared_calibrator_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_forecast_common actual
exit $?
