#!/usr/bin/env bash
# Positive suffix1 cost8 with identical input/head logits; stop on gradient or integrity error, checkpoint0.
# Independent fresh outputs; no stdin/implicit resume. Prerequisite HOLD is explicit.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al1Wc_suffix_positive_cost8_"$stamp" --note 'Positive suffix1 cost8 with identical input/head logits; stop on gradient or integrity error, checkpoint0.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al1Wc_suffix_positive_cost8_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode cost --arm auxdense100 --execute --max-wall-sec 600
