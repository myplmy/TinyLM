#!/usr/bin/env bash
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWc_wsl_sparse24_inference_attribution \
  --note "P025B Stage0bWc: one-way inference pack versus bidirectional training pack by M; packing excluded; synthetic kernel gate, not trained-model inference" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWc_wsl_sparse24_inference_attribution -- \
  "$python_bin" scripts/diag_sparse24_inference_attribution.py --require-wsl \
  --m-values 1,16,128,1024,8192 --warmup 10 --iters 30 --prefill-speedup 1.10
