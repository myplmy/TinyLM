#!/usr/bin/env bash
# P095 S0 synthetic CPU contract only. No model/checkpoint/GPU access.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" -B -X utf8 scripts/diag_scout_memory_contract.py
