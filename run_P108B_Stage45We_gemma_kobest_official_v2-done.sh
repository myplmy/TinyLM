#!/usr/bin/env bash
# Existing Gemma270/official KoBEST;entry-order v2 preserves failed v1.
# Same-process cache/import/source CPU check before any model loading.
# Estimate2-12min;15min bound. No install,training or checkpoint writes.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin=/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 HF_EVALUATE_OFFLINE=1 USE_HUB_KERNELS=0
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_external_gemma_kobest_v2 entry-check
fi
"$python_bin" -B -m scripts.diag_p108b_external_gemma_kobest_v2 entry-check || exit $?
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B scripts/runlog.py --num 108 --name P108B_Stage45We_gemma_kobest_official_v2 -- "$python_bin" -B -u -m scripts.diag_p108b_external_gemma_kobest_v2 actual
exit $?
