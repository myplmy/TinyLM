#!/usr/bin/env bash
# Stage0aWb mixed PyTorch's expected forced-backend diagnostics into raw warning
# spam. This rerun records each unavailable backend and its reason on one row.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0aWc_wsl_sdpa_gqa_backend \
  --note "P060B Stage0aWc: capture forced SDPA backend warnings per variant so successful FLASH/CUDNN and unavailable EFFICIENT are not conflated" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 088 --name P060B_Stage0aWc_wsl_sdpa_gqa_backend -- \
  "$python_bin" scripts/diag_sdpa_wsl_gqa.py --require-wsl --warmup 5 --iters 20 \
  --max-speed-ratio 1.05 --min-memory-reduction 0.10
