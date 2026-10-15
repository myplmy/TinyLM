#!/usr/bin/env bash
# Choose from completed five-arm final DEV only, never fresh test. Not automatic adoption.
# Independent fresh outputs; explicit gates; no stdin, downloads or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aq2W_large_binding_choice_"$stamp" --note 'Choose from completed five-arm final DEV only, never fresh test. Not automatic adoption.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aq2W_large_binding_choice_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_scale.py --mode choice --execute
