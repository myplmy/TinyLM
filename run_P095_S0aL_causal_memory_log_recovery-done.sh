#!/usr/bin/env bash
# P095 S0aL durable-log recovery of the already observed synthetic CPU contract.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" -B -X utf8 scripts/runlog.py \
    --name P095_S0aL_causal_memory_log_recovery -- \
    "$python_bin" -B -X utf8 scripts/diag_scout_memory_contract.py
