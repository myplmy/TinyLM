#!/usr/bin/env bash
# Existing Gemma270 FP32/native HF and unchanged official KoBEST five tests.
# Estimate2-12min;15min bound. No install,training or checkpoint writes.
# Source/assets/task preflight is mandatory;keep every failed/partial raw.
# A full official score is an external baseline,not TinyLM improvement.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin=/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_EVALUATE_OFFLINE=1 USE_HUB_KERNELS=0
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_external_gemma_kobest check
fi
"$python_bin" -B -m scripts.diag_p108b_external_gemma_kobest check || exit $?
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B scripts/runlog.py --num 108 --name P108B_Stage45Wb_gemma_kobest_official -- "$python_bin" -B -u -m scripts.diag_p108b_external_gemma_kobest actual
exit $?
