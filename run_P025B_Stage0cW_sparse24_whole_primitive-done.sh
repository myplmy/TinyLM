#!/usr/bin/env bash
# P025B Stage0cW: forward+dgrad+dense-wgrad with explicit pack amortization.
set -u -o pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

exec "$python_bin" scripts/runlog.py --num 082 --name P025B_Stage0cW_sparse24_whole_primitive -- \
  "$python_bin" scripts/diag_sparse24_whole_primitive.py \
    --require-wsl --m 8192 --accum 16 --warmup 3 --iters 10 \
    --pack-repeats 5 --min-speedup 1.10
