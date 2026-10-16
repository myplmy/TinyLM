#!/usr/bin/env bash
# Closed actual execution; exact scope/raw result preserved, not global quality PASS.
# New isolated complete-smoke observation; no stdin or old-output overwrite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ekW_final_authorized_smoke_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ekW_final_authorized_smoke_"$run_stamp" --num 101 --note 'Authorized complete44-arm Codex-adapted smoke in a new isolated namespace. Canonical model/training flags unchanged; original synthetic hashes checked, offline/WandB disabled. Runtime is not model quality or new-session Codex E2E.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ekW_final_authorized_smoke_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_final_smoke.py --mode full --execute
