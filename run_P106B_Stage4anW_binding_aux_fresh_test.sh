#!/usr/bin/env bash
# Five arms required: original inference path without auxiliary head, fresh code640 and fixed pseudo QA16 per model.
# Independent fresh outputs; stop on prerequisite/error. No stdin or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4anW_binding_aux_fresh_test_"$stamp" --note 'Five arms required: original inference path without auxiliary head, fresh code640 and fixed pseudo QA16 per model. Code greedy64/public greedy256 within disclosed model context cap.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4anW_binding_aux_fresh_test_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode evaluate --execute --max-wall-sec 1800
