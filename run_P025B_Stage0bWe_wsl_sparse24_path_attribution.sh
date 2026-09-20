#!/usr/bin/env bash
# P025B Stage0bWe: split synchronized wall, CUDA-event batch, host enqueue,
# padding, profiler and CUDA Graph evidence. Synthetic FP16 GEMM; training 0.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWe_wsl_sparse24_path_attribution \
  --note "P025B Stage0bWe: preserve Wd negative and split PyTorch dispatch, padding, GPU-op and graph overhead without TLinear integration" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWe_wsl_sparse24_path_attribution -- \
  "$python_bin" scripts/diag_sparse24_path_attribution.py --require-wsl --mode attribute \
  --m-values 1,8,128,8192 --layouts inference,training --rounds 3 --warmup 5 \
  --iters 20 --profile-iters 3 --cuda-graph --max-nrms 0.001 \
  --max-abs-ratio 0.01 --min-cosine 0.999999
