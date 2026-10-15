#!/usr/bin/env bash
# Same176 SFT/native updates, causal query-suffix auxiliary1. Inference uses original model only.
# Independent fresh outputs; no stdin/implicit resume. Prerequisite HOLD is explicit.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWe_binding_aux_causal_suffix_"$stamp" --note 'Same176 SFT/native updates, causal query-suffix auxiliary1. Inference uses original model only.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4amWe_binding_aux_causal_suffix_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_auxiliary.py --mode train --arm auxdense100 --execute --max-wall-sec 3600
