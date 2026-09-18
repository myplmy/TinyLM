#!/usr/bin/env bash
# P025B corrected WSL CUDA gate: split one-way inference pack from bidirectional training pack.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?

printf '%s\n' '[P025B Stage0bWb] WSL native 2:4 packing-direction/forward/input-gradient/speed gate'
printf '%s\n' 'This is a GPU diagnostic, not training or a quality result.'
exec "$python_bin" -B -X utf8 scripts/runlog.py \
    --name P025B_Stage0bWb_wsl_sparse24_training_pack -- \
    "$python_bin" -B -X utf8 scripts/diag_sparse24_backend.py \
    --require-wsl --m 8192 --warmup 10 --iters 30
