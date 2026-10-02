#!/usr/bin/env bash
# P106B_Stage3iWi_online_technical_collection: expected 4.00h. Current pilot prerequisite; full96 groups, minimum75 percent technical material each language, truth unreviewed; no student.
# New stage/version only; originals preserved; every prerequisite failure stops this launcher.
# No interactive input. CPU/static success does not imply new teacher/student quality.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3iWi_online_technical_collection.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3iWi_online_technical_collection --num 101 --note 'Current pilot prerequisite; full96 groups, minimum75 percent technical material each language, truth unreviewed; no student. Read raw answers and report domains separately. Admission is not truth; no stdin wait.'
"$python_bin" scripts/runlog.py --name P106B_Stage3iWi_online_technical_collection --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --check-only --mode correct
"$python_bin" scripts/runlog.py --name P106B_Stage3iWi_online_technical_collection --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_education_followup.py --execute --mode correct
