#!/usr/bin/env bash
# P095 S0bT: user-run tiny Transformer + Scout first-coda integration gate.
# CPU-only synthetic tokens, no checkpoint or training corpus. Estimate 0.2 h.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)"
"$python_bin" scripts/runlog.py --name P095_S0bT_coda_wiring --note "P095 opt-in first-coda Scout memory wiring; CPU model gate, default backbone unchanged."
"$python_bin" scripts/runlog.py --name P095_S0bT_coda_wiring -- "$python_bin" -B -X utf8 scripts/diag_p095_s0bt_coda.py --check-only
"$python_bin" scripts/runlog.py --name P095_S0bT_coda_wiring -- "$python_bin" -B -X utf8 scripts/diag_p095_s0bt_coda.py
