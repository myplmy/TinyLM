#!/usr/bin/env bash
# User GPU estimate0.50h/max60min. Conditional on contract16 success.
# No stdin/download/student/checkpoint writes. Existing data never replaced.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4iWd_family64_production_pilot.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iWd_family64_production_pilot --num 101 --note 'User GPU0.50h/max60min; successful contract16 and new smoke required. Family-stratified KOEN32 each/real-family<=8/QA16-json8-producer-state3turn8. No repeated filler/topic-certification/75M claim. Same teacher budgets,3 structural attempts,20MB/raw/thoughts/provenance. Accepted nonpadding x and whole-wall supply measured; no student training.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iWd_family64_production_pilot --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_task_pilot.py --mode family64 --execute
