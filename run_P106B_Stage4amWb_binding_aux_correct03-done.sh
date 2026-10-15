#!/usr/bin/env bash
# Completed2026-10-15 raw100600 exit0;176 actual updates, final test pending.
# Same176 updates with producer-correct requested-first auxiliary coefficient0.3; inference head absent.
# Independent fresh outputs; stop on prerequisite/error. No stdin or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWb_binding_aux_correct03_"$stamp" --note 'Same176 updates with producer-correct requested-first auxiliary coefficient0.3; inference head absent.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWb_binding_aux_correct03_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode train --arm aux03 --execute --max-wall-sec 3600
