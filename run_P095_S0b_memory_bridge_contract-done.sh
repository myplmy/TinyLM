#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 087 --name P095_S0b_memory_bridge_contract \
  --note "P095 S0b: default-off hidden bridge identity, causal prefix invariance, reset determinism, physical state bytes, CPU latency and finite backward; full Transformer wiring/training remain separate" || exit $?
exec "$python_bin" scripts/runlog.py --num 087 --name P095_S0b_memory_bridge_contract -- \
  "$python_bin" scripts/diag_scout_memory_integration.py --steps 24 --iters 20
