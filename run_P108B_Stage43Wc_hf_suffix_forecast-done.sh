#!/usr/bin/env bash
# Reuse native Gemma270 layer17 packet;two-norm/softcap suffix forecast only.
# Twelve existing calibration inputs and three fixed scales;no training.
# Estimate1-5min;10min cap;no generation,install or checkpoint writes.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin=/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 USE_HUB_KERNELS=0
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_hf_suffix_forecast check
fi
"$python_bin" -B -m scripts.diag_p108b_hf_suffix_forecast check || exit $?
timeout --signal=TERM --kill-after=20s 720s "$python_bin" -B scripts/runlog.py --num 108 --name P108B_Stage43Wc_hf_suffix_forecast -- "$python_bin" -B -u -m scripts.diag_p108b_hf_suffix_forecast actual
exit $?
