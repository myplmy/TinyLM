#!/usr/bin/env bash
# User-run WSL CUDA/cuSPARSELt re-probe. This script performs no training.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

printf '%s\n' '[P025B Stage0bW] WSL native 2:4 forward/input-gradient/speed gate'
printf '%s\n' 'This is a GPU diagnostic, not a training or quality result.'
exec "$python_bin" -B -X utf8 scripts/runlog.py \
    --name P025B_Stage0bW_wsl_sparse24_backend -- \
    "$python_bin" -B -X utf8 scripts/diag_sparse24_backend.py \
    --require-wsl --m 8192 --warmup 10 --iters 30
