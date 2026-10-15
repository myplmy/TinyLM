#!/usr/bin/env bash
# Reference the same original736 deck by SHA; no teacher or new unique world-source claim.
# Fresh namespace, no stdin/implicit resume/old mutation; fail closed on prerequisite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ao0Wb_verbatim_deck_"$stamp" --note 'Reference the same original736 deck by SHA; no teacher or new unique world-source claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ao0Wb_verbatim_deck_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_verbatim_source.py --mode freeze --execute
