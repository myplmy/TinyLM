#!/usr/bin/env bash
# Reuse48 frozen values; optimize only120 missing fact-layer pairs.
# About30-60min, at least4GiB free. Same sealed optimizer/shift/40steps.
# Single dependent phase; original checkpoints and completed candidates intact.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -c 'from scripts.diag_p108b_value_library import verify; verify(); print("[CHECK_ONLY] frozen profile/source/authority verified; GPU NOT_RUN")'
fi
"$python_bin" -B -c 'import json; from scripts.diag_p108b_value_library import BASE; reports=[json.loads(p.read_text()) for p in (BASE/"canary").glob("report_*.json")]; assert any(r.get("status")=="FULL14_ZERO_PARITY_AND_VALUE_GRADIENT_VERIFIED" and r.get("registered_core_unchanged") and len(r.get("layers",[]))==14 and r.get("cuda_allocated_after_bytes")==0 for r in reports), "successful same-origin full14 canary required"' || exit 2
resume=()
if [[ "${1:-}" == --resume ]]; then resume=(--resume); fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wa_missing10_value_library --num 108 --note 'Nov16 directive140 before13KST. Requires successful full14 canary. Reuse original4layers/48values. Only missing10layers times12groups times40 auxiliary updates; base optimizer and CP0. Oracle per-fact success is not one global model. Preserve input/labels/core and exact old value recipe; partial resume must be explicit. Read168-grid completion/exposures/core/CUDA before actual weight writes.'
timeout --signal=TERM --kill-after=20s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wa_missing10_value_library --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_value_library run "${resume[@]}"
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wa_missing10_value_library --num 108 --note "Final value-library exit=$result. Check all168 pairs, auxiliary exposure and unchanged original. Quality of actual shared/global writes remains separate."
exit "$result"
