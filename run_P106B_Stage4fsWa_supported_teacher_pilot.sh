#!/usr/bin/env bash
# New visible-source/MTP teacher pilot. Four generated groups, max10min.
# Same parser/sampler/thinking; no student, download, old overwrite or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_supported_production8h
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWa_supported_teacher_pilot_"$stamp" --num 101 --note 'Visible-source pilot only. Old4473 preserved but not admitted; original source cursor retained. Complete quoted evidence in student first question, no truncation/semantic blacklist. >=4 accepted new candidates required before8h production. Exit8 can mean bounded pause, not student failure.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWa_supported_teacher_pilot_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode pilot --max-wall-sec 600 --execute
