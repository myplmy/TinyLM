#!/usr/bin/env bash
# User158 until17Nov17KST; prepared original8 PTS cases, no training.
# Native original FP32/eager tolerance; first negative closes without shrink/retry.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export PYTHONIOENCODING=utf-8 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export CUDA_CACHE_PATH="$PWD/test_result/evidence/p106b_dvlm_native_v1_20261117/runtime_cache/cuda"
export CUDA_CACHE_MAXSIZE=33554432
export TRITON_CACHE_DIR="$PWD/test_result/evidence/p106b_dvlm_native_v1_20261117/runtime_cache/triton"
export TORCHINDUCTOR_CACHE_DIR="$PWD/test_result/evidence/p106b_dvlm_native_v1_20261117/runtime_cache/inductor"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_dvlm_native check
fi
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dv0Wd_dvlm_native --note 'Current158 fixed8 original-order cases after CPU21+native6. FP32/eager/noKV, atol1e-5 rtol1e-4. PTS HPA versus independent group-serial causal hidden, original head0. No optimizer/newCP/quality claim. Model and source hashes close, one owned GPU, phase1200s, cutoff16:40KST. STOP=test_result/evidence/p106b_dvlm_native_v1_20261117/STOP. Exit2 preserves numerical negative, exit8 preserves budget HOLD; no automatic retry.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dv0Wd_dvlm_native -- timeout --signal=INT --kill-after=120s 1200s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_dvlm_native actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dv0Wd_dvlm_native --note "Actual shell exit=$result. Preserve partial packets, original tolerance, state/source and CUDA release proof. Head initialization/training and formal quality remain separate."
exit "$result"
