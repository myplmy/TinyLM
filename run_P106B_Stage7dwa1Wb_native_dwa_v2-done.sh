#!/usr/bin/env bash
# User158; existing native teacher-cache and student, zero-update CE/DWA ABBA.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export PYTHONIOENCODING=utf-8 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
export CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_CACHE_DISABLE=1
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
export TRITON_CACHE_DIR="$PWD/test_result/evidence/p106b_dwa_native_v2_20261117_s1337/runtime_cache/triton"
export TORCHINDUCTOR_CACHE_DIR="$PWD/test_result/evidence/p106b_dwa_native_v2_20261117_s1337/runtime_cache/inductor"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_dwa_native_v2 check
fi
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dwa1Wb_native_dwa_v2 --note 'User158: new current-window native DWA after frozen CMA12/boundary5. Reuse closed original128 Qwen3.5 features;teacher body0. Exact new595-broad-q, full student32768/teacher248320 heads, micro1x128,original772/811 native targets, global772 denominator. CE/DWA/DWA/CE zero updates;4 seeded bias-free projectors, FP64 existing DTWv2. Native STE BF16 body/FP32 dual space/TF32off. No training quality/newCP/install/download. First DWA includes JIT. Original157 plus declared0/4 projector gradients, exact same-arm repeat/source/state/hash and owned cleanup. Compute1800s/phase1920s;allocator cap8GiB;cutoff16:40KST. STOP=test_result/evidence/p106b_dwa_native_v2_20261117_s1337/STOP. Exit8 HOLD/1 error/9 closure;no automatic retry.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dwa1Wb_native_dwa_v2 -- timeout --signal=INT --kill-after=60s 1920s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_dwa_native_v2 actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage7dwa1Wb_native_dwa_v2 --note "Actual shell exit=$result. Full original targets and all blocks or explicit remaining NOT_RUN;preserve source/grad/state/cache release and failed preparations. Zero-update engineering only;whole DWA training/quality remains separate."
exit "$result"
