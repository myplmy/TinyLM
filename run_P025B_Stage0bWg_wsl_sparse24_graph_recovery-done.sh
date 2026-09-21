#!/usr/bin/env bash
# P025B Stage0bWg: recover the pre-replay CUDA Graph comparison defect. Training 0.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

exec "$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWg_wsl_sparse24_graph_recovery -- \
  "$python_bin" scripts/diag_sparse24_path_attribution.py --require-wsl --mode attribute \
  --m-values 1,8192 --layouts inference,training --rounds 2 --warmup 3 --iters 10 \
  --profile-iters 0 --cuda-graph --require-cuda-graph \
  --max-nrms 0.001 --max-abs-ratio 0.01 --min-cosine 0.999999
