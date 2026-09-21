#!/usr/bin/env bash
# P022C Stage0bWc: A-E same-session attribution with cached FP8 weight as the
# primary candidate. Synthetic forward only; TLinear/backward/training NOT_RUN.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

"$python_bin" scripts/runlog.py --num 081 --name P022C_Stage0bWc_fp8_path_attribution \
  --note "P022C Stage0bWc: separate prepared GEMM, cached weight, delayed and current scaling with independent speed memory and numerical gates" \
  || exit $?
exec "$python_bin" scripts/runlog.py --num 081 --name P022C_Stage0bWc_fp8_path_attribution -- \
  "$python_bin" scripts/diag_fp8_path_attribution.py --require-wsl --m 8192 \
  --rounds 3 --warmup 5 --iters 20 --profile-iters 3 --min-speedup 1.10 \
  --max-memory-ratio 1.00 --max-nrms 0.03 --min-cosine 0.999
