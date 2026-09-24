#!/usr/bin/env bash
# P101A Stage1W: pinned M0 checkpoint migration and tiny same-input function gate.
# About 0.2 h CPU, several GiB host RAM. User-run model loading; no GPU training.
# Failure is a hard functionality failure; it must not be recoded as scientific exit 8.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage1W_m0_migration_gate --note "Pinned M0 parent/tokenizer/cache SHA first; strict E384/QK/MTP state migration, main-logit preservation, auxiliary gradients and deploy removal. CPU model gate only; no 100M training approval."
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage1W_m0_migration_gate -- "$python_bin" -B -X utf8 scripts/diag_p101a_m0_migration.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P101A M0 migration gate rc=$rc" >&2
    exit "$rc"
fi
echo "[PASS] P101A M0 CPU gate completed; GPU quality remains NOT_RUN"
