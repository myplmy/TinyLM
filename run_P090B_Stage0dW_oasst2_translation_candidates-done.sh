#!/usr/bin/env bash
# P090B Stage0dW: pinned public OASST2 English translation-candidate audit.
# Read-only CPU; no raw text output, translation, model or GPU.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0dW_oasst2_translation_candidates --note "Reviewed non-synthetic English tree paths, exact v3 first-prompt disjointness, legacy mask/length, 200 candidate IDs and 50 human-review IDs only; no translation or TRAIN_READY claim."
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0dW_oasst2_translation_candidates -- "$python_bin" -B -X utf8 scripts/diag_p090b_oasst2_translation_candidates.py --self-test
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P090B OASST2 branch fixture rc=$rc" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 096 --name P090B_Stage0dW_oasst2_translation_candidates -- "$python_bin" -B -X utf8 scripts/diag_p090b_oasst2_translation_candidates.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P090B OASST2 candidate audit rc=$rc" >&2
    exit "$rc"
fi
echo "[HOLD] P090B translation-candidate IDs only; human QA and Korean translation NOT_RUN"
