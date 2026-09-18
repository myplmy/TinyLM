#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 080 --name P091_R2_layer_state_selector \
  --note "P091 R2: actual TinyLM tiny-model gate-zero S and weight-decay-separated optimizer update U across three deterministic windows; R3 realized-gain prediction remains separate" || exit $?
exec "$python_bin" scripts/runlog.py --num 080 --name P091_R2_layer_state_selector -- \
  "$python_bin" scripts/diag_layer_state_selector.py --windows 3
