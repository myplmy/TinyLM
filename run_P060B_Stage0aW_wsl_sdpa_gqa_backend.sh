#!/usr/bin/env bash
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --name P060B_Stage0aW_wsl_sdpa_gqa_backend \
  --note "P060B Stage0aW: PyTorch native SDPA GQA correctness, forced backend speed and working-memory attribution on WSL; training 0" \
  || exit $?
exec "$python_bin" scripts/runlog.py --name P060B_Stage0aW_wsl_sdpa_gqa_backend -- \
  "$python_bin" scripts/diag_sdpa_wsl_gqa.py --require-wsl --warmup 5 --iters 20 \
  --max-speed-ratio 1.05 --min-memory-reduction 0.10
