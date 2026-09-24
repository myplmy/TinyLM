#!/usr/bin/env bash
# P090B Stage0cW: pinned public Korean multi-turn source, read-only CPU gate.
# Structural candidates only; human quality, PII, license and contamination NOT_RUN.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0cW_empathetic_multiturn_contract --note "Pinned Korean multi-turn marker/role restoration; no raw text output. Structural PARTIAL is a candidate result, not TRAIN_READY."
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0cW_empathetic_multiturn_contract -- "$python_bin" -B -X utf8 scripts/diag_p090b_empathetic_contract.py --self-test
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P090B strict parser fixture rc=$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0cW_empathetic_multiturn_contract -- "$python_bin" -B -X utf8 scripts/diag_p090b_empathetic_contract.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P090B public source structural audit rc=$rc" >&2
    exit "$rc"
fi
echo "[HOLD] P090B candidate structure only; human quality and train readiness NOT_RUN"
