#!/usr/bin/env bash
# Reuse48 frozen values; complete only120 pairs with unchanged40-step recipe.
# About30-60min,4GiB free; v2 full14 canary is a strict prerequisite.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -c 'from scripts.diag_p108b_value_library import verify; verify(); print("[CHECK_ONLY] v2 source/profile/authority verified; GPU NOT_RUN")'
fi
"$python_bin" -B -c 'import json; from scripts.diag_p108b_value_library import BASE; reports=[json.loads(p.read_text()) for p in (BASE/"canary").glob("report_*.json")]; assert any(r.get("status")=="FULL14_ZERO_PARITY_AND_VALUE_GRADIENT_VERIFIED" and r.get("registered_core_unchanged") and len(r.get("layers",[]))==14 and r.get("cuda_allocated_after_bytes")==0 and r.get("cuda_reserved_after_bytes")==0 for r in reports), "same-origin full14 zero-allocation canary required"' || exit 2
resume=()
if [[ "${1:-}" == --resume ]]; then resume=(--resume); fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wb_missing10_value_library --num 108 --note 'Nov16 directive140 before13KST. Same complete Broad-F and old4layers48values. Only missing10layers120values4800 auxiliary updates; no body optimizer/new300M/CP writes. Preserve target exposures and per-fact oracle vs one global model distinction. Existing strict CUDA cleaner; explicit same-source resume only.'
timeout --signal=TERM --kill-after=20s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wb_missing10_value_library --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_value_library run "${resume[@]}"
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage24Wb_missing10_value_library --num 108 --note "Final library exit=$result; read168-grid/core/exposures/CUDA. Actual edited global model quality remains to be measured."
exit "$result"
