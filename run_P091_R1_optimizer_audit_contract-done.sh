#!/usr/bin/env bash
# P091 R1 CPU contract only. No model/checkpoint/GPU access.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" -B -X utf8 scripts/runlog.py \
    --name P091_R1_optimizer_audit_contract -- \
    "$python_bin" -B -X utf8 scripts/diag_optimizer_audit_contract.py
