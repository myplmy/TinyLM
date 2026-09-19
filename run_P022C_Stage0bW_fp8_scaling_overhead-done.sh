#!/usr/bin/env bash
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/shell/tinylm_env.sh
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 081 --name P022C_Stage0bW_fp8_scaling_overhead \
  --note "P022C C1: same-session BF16 versus FP8 current/delayed scaling with absmax, cast, scaled_mm, correctness and peak allocation; backward/training 0" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 081 --name P022C_Stage0bW_fp8_scaling_overhead -- \
  "$python_bin" scripts/diag_fp8_scaling_overhead.py --require-wsl --m 8192 \
  --warmup 10 --iters 30 --min-speedup 1.10 --max-nrms 0.03 --min-cosine 0.999
