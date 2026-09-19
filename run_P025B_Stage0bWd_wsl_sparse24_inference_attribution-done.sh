#!/usr/bin/env bash
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWd_wsl_sparse24_inference_attribution \
  --note "P025B Stage0bWd: Stage0bWc used elementwise tolerance as the sole gate and stopped at the first failed row; this rerun uses normalized RMS plus cosine and completes every shape" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0bWd_wsl_sparse24_inference_attribution -- \
  "$python_bin" scripts/diag_sparse24_inference_attribution.py --require-wsl \
  --m-values 1,16,128,1024,8192 --warmup 10 --iters 30 --prefill-speedup 1.10 \
  --max-nrms 0.001 --max-abs-ratio 0.01 --min-cosine 0.999999
