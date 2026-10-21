#!/usr/bin/env bash
# V3 recovery: V2 collected4 groups then scanned7.29M ineligible rows until owned TERM.
# Move pilot cap/STOP check ahead of quota filtering. V1/V2 raw remains immutable.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_supported_production8h
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWac_supported_teacher_bounded_pilot_"$stamp" --num 101 --note 'V3 source-filter cap recovery; old4 accepted/943train tokens and controlled TERM preserved. New cap and STOP run before eligibility,4generated groups/600sec. Same teacher/MTP/sampling/thinking, full visible source and exact raw/candidate gate. Not semantic or75M PASS.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWac_supported_teacher_bounded_pilot_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode pilot --max-wall-sec 600 --execute
