#!/usr/bin/env bash
# Same176 updates with producer-correct requested-first auxiliary coefficient1.0; not a truth selector.
# Independent fresh outputs; stop on prerequisite/error. No stdin or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWc_binding_aux_correct100_"$stamp" --note 'Same176 updates with producer-correct requested-first auxiliary coefficient1.0; not a truth selector.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWc_binding_aux_correct100_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode train --arm aux100 --execute --max-wall-sec 3600
