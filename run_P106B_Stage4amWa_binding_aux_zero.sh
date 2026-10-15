#!/usr/bin/env bash
# Control: same176 SFT/native updates, all known binding-head forwards computed, auxiliary gradient0.
# Independent fresh outputs; stop on prerequisite/error. No stdin or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWa_binding_aux_zero_"$stamp" --note 'Control: same176 SFT/native updates, all known binding-head forwards computed, auxiliary gradient0.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWa_binding_aux_zero_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode train --arm aux0 --execute --max-wall-sec 3600
