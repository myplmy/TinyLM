#!/usr/bin/env bash
# Executed20261017; raw status and exact commands retained before cleanup.
# Separate64-root bare-parent panel; trained512-root evaluation unchanged.
# No stdin/training/weights writes; partial old full512 parent is not complete.
# Approval expires2026-10-17 10:00KST; GPU stops09:00KST.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4dq0Wb_parent_panel_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw log preserved; use a new stage/tag.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dq0Wb_parent_panel_cpu_"$run_stamp" --num 101 --note 'Separate source-hash-selected64 KO/EN roots, original3 views/128-token cap; English768 MC and fixed native windows. Trained four endpoints retain full512/eight lanes. No completion of old six-endpoint gate, no threshold relaxation or general truth claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4dq0Wb_parent_panel_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_night_parent_panel.py --mode freeze --execute
