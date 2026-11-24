#!/usr/bin/env bash
# Same DEV-frozen edit;reuse exact official11 prompts and original baseline.
# Estimate5-20min;30min bounded. No fit, install or checkpoint writes.
# Read official metrics and raw paired transitions;loss alone cannot adopt.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin=/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_EVALUATE_OFFLINE=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_pm_evaluate check
fi
"$python_bin" -B -m scripts.diag_p108b_pm_evaluate check || exit $?
timeout --signal=TERM --kill-after=20s 1920s "$python_bin" -B scripts/runlog.py --num 108 --name P108B_Stage41Wd_frozen_official11 -- "$python_bin" -B -u -m scripts.diag_p108b_pm_evaluate official
exit $?
