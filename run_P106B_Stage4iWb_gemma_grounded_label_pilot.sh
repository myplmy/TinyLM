#!/usr/bin/env bash
# User GPU0.75h/max60min; oldpilot held. Requires newlabel off8/8,not MTP adoption.
# Existing logs/outputs stay immutable; no stdin/download/teacher-owned JSON.
# New smoke first. Exit8 is gate-negative/HOLD,9 is tool failure.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4iWb_gemma_grounded_label_pilot.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iWb_gemma_grounded_label_pilot --num 101 --note 'User GPU0.75h/max60min; pinnedsource inventory and newGemma label role off8/8 fields/context/mask required. Same16 distinct originalgroups/KOEN8/QA-json-3turn,shared3 structural attempts,20MB/raw/thoughts/provenance. MTPoff,no student/75M claim; priorHOLD retained,new smoke first.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iWb_gemma_grounded_label_pilot --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_grounded_gemma_label_pilot.py --execute
