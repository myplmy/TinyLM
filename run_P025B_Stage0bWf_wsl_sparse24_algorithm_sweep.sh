#!/usr/bin/env bash
# P025B Stage0bWf: low-level PyTorch alg_id/Split-K probe followed by a fresh
# confirmation comparison. Search timing is never reused as final evidence.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWf_wsl_sparse24_algorithm_sweep \
  --note "P025B Stage0bWf: probe conservative alg_id and Split-K candidates, then confirm the selected row apart from search" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWf_wsl_sparse24_algorithm_sweep -- \
  "$python_bin" scripts/diag_sparse24_path_attribution.py --require-wsl --mode tune \
  --m-values 1,128,1024,8192 --layouts inference --alg-ids 0,1,2,3,4 \
  --split-k-values 1,2,4 --split-k-modes 0,1 --rounds 3 --warmup 5 --iters 20 \
  --tune-warmup 3 --tune-iters 10 --profile-iters 3 --min-speedup 1.10 \
  --max-nrms 0.001 --max-abs-ratio 0.01 --min-cosine 0.999999
