#!/usr/bin/env bash
# Same original scales and exact old gates, now on the CPU target.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/miniforge3/envs/tlm_torch/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export TRITON_CACHE_DIR="$PWD/test_result/evidence/p014e_direct_packed_v1_s1337/runtime_cache/triton"
export CUDA_CACHE_PATH="$PWD/test_result/evidence/p014e_direct_packed_v1_s1337/runtime_cache/cuda"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p014e_direct_cpu check
fi
"$python_bin" -B -m scripts.diag_p014e_direct_cpu check || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --name P014E_Stage6Wb_cpu_direct_operators --num 099 -- "$python_bin" -B -u -m scripts.diag_p014e_direct_cpu actual
exit $?
