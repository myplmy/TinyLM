#!/usr/bin/env bash
# User GPU up to6h. Successful newV3 pilots plus pinnedC/public inputs before teacher. Fresh deficitV3; rootconcept/KOEN/task/val/source quotas,20MB raw/canonical; PAUSED8 is not75M completion.
# User-run only; no stdin/download. Exit8 prerequisite/negative,9 tool error.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4jWe_literal_deficit_production"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4jWe_literal_deficit_production --num 101 --note 'User GPU up to6h. Successful newV3 pilots plus pinnedC/public inputs before teacher. Fresh deficitV3; rootconcept/KOEN/task/val/source quotas,20MB raw/canonical; PAUSED8 is not75M completion.'
"$python_bin" scripts/runlog.py --name P106B_Stage4jWe_literal_deficit_production --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode produce --execute --max-wall-sec 21600
