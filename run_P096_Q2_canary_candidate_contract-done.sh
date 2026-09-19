#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 085 --name P096_Q2_canary_candidate_contract \
  --note "P096 Q2: bounded 450-slot, at-most-two-candidates provenance/preservation/semantic contract on synthetic Q1b fixtures; protected items and text generation remain NOT_RUN" || exit $?
exec "$python_bin" scripts/runlog.py --num 085 --name P096_Q2_canary_candidate_contract -- \
  "$python_bin" scripts/diag_heldout_canary_contract.py
