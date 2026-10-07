#!/usr/bin/env bash
# User GPU0.75h/max60min; after source inventory and Gemma base role wiring.
# Source-supported B16 groups/KOEN8,QA4/JSON2/dialogue2,up to3 structural attempts.
# MTPoff baseline; olddata preserved/newshards20MB,raw/thoughts/provenance retained.
# No stdin/student/checkpoint/75M claim. Time is a pilot, not guaranteed bulk rate.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4iW_gemma_grounded_pilot.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iW_gemma_grounded_pilot --num 101 --note 'User GPU0.75h/max60min; requires source inventory/Gemma asset+base role wiring/newsmoke. Grounded B16 groups/KOEN8/QA-json-dialogue,shared3 structural attempts per turn,no wrong-phrase list. Real source families/raw/thoughts/20MB retained; student/75M NOT_RUN.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iW_gemma_grounded_pilot --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_grounded_gemma_pilot.py --execute
