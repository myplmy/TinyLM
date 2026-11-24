#!/usr/bin/env bash
# Same native Gemma18 directions and held-out scales, one technical FIT case.
# About1-3min,4GiB free; no training, generated answers or quality claim.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
eval_python="./data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$eval_python" -B -m scripts.diag_p108b_prediction_scale check; fi
"$eval_python" -B -m scripts.diag_p108b_prediction_scale check || exit $?
timeout --signal=TERM --kill-after=20s 360s "$eval_python" -B -X utf8 scripts/runlog.py --name P108B_Stage33Wc_gemma_step_prediction --num 108 -- "$eval_python" -B -u -m scripts.diag_p108b_prediction_scale actual --arm gemma
exit $?
