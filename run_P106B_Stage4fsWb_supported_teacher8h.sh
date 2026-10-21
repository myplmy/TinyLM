#!/usr/bin/env bash
# New namespace only after exact four-candidate pilot; max8h, no student.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWb_supported_teacher8h_"$stamp" --num 101 --note 'Produce up to8h, not a75M completion promise. Ctrl+C/TERM or OUTPUT/STOP closes new immutable batch; resume uses new batch/cursor and verifies hashes. Hard kill/partial unpublished batch requires inspection, never automatic truncation. No quality PASS.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWb_supported_teacher8h_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode produce --max-wall-sec 28800 --execute
