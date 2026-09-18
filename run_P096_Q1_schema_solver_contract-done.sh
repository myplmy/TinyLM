#!/usr/bin/env bash
# P096 Q1 synthetic schema/solver contract. It never reads datasets/TinyDataset.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" -B -X utf8 scripts/runlog.py \
    --name P096_Q1_schema_solver_contract -- \
    "$python_bin" -B -X utf8 scripts/diag_heldout_contract.py
