#!/usr/bin/env bash
# P093 GPU-free overlap and sharing accounting gate.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" -B -X utf8 scripts/runlog.py \
    --name P093_Stage0ab_sharing_accounting -- \
    "$python_bin" -B -X utf8 scripts/diag_sharing_accounting.py
