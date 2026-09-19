#!/usr/bin/env bash
# Stage0bW returned exit 4 after valid measurements because an unapproved NRMS
# screen was treated as an execution failure. This rerun preserves the metrics
# and returns the declared scientific-negative code when speed/memory fail.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 081 --name P022C_Stage0bWb_fp8_scaling_overhead \
  --note "P022C Stage0bWb: Stage0bW measured valid rows but mislabeled the scientific numeric/speed negative as execution failure; corrected gate classification" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 081 --name P022C_Stage0bWb_fp8_scaling_overhead -- \
  "$python_bin" scripts/diag_fp8_scaling_overhead.py --require-wsl --m 8192 \
  --warmup 10 --iters 30 --min-speedup 1.10 --max-nrms 0.03 --min-cosine 0.999
