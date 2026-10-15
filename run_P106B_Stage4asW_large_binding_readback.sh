#!/usr/bin/env bash
# Parent and two final students, fresh640 plus dev16/legacy8/live4. No training.
# Independent fresh outputs; explicit gates; no stdin, downloads or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4asW_large_binding_readback_"$stamp" --note 'Parent and two final students, fresh640 plus dev16/legacy8/live4. No training.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4asW_large_binding_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_scale.py --mode evaluate --execute --max-wall-sec 2400
