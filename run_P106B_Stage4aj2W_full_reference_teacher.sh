#!/usr/bin/env bash
# Fresh deck required; Gemma12B/MTP ON alone. About2h GPU upper planning bound.
# Same8192/3072/1024 sampler; every bounded original span reaches student, not only selected IDs.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj2W_full_reference_teacher_"$stamp" --note 'Teacher-only new512 train/64val source block. Full bounded original reference visible; raw/thinking local, ANSWER only target. Structural retry max3, no semantic word list. Record real supply/output/time and measurement gaps, not world truth.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj2W_full_reference_teacher_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_expand.py --mode generate --execute --max-wall-sec 7200
