#!/usr/bin/env bash
# P091 actual TinyLM CPU model ownership/audit mapping gate; includes the R1a regression.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
exec "$python_bin" -B -X utf8 scripts/runlog.py \
    --name P091_R0R1b_model_mapping_audit -- \
    "$python_bin" -B -X utf8 scripts/diag_layer_state_mapping.py
