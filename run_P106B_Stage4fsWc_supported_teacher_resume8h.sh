#!/usr/bin/env bash
# Explicit continuation, at most8h; old reports and raw remain immutable.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWc_supported_teacher_resume8h_"$stamp" --num 101 --note 'Explicit resume: exact same inputs/code and4-candidate support pilot required. Move prior STOP file before resume. Any incomplete batch is HOLD, not silent reset. Source attempts do not get a fresh retry budget. Separate raw shards below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fsWc_supported_teacher_resume8h_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_supported_production8h.py --mode resume --max-wall-sec 28800 --execute
