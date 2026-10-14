#!/usr/bin/env bash
# Same-code supply inventory required; fresh deck only. About0.08h CPU, no models.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj1W_source_expand_deck_"$stamp" --note 'Freeze new736 deck only after matching inventory/code/source SHA. Old corpus/root/source bytes remain unchanged. Model0, teacher generation is a separate gate.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aj1W_source_expand_deck_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_expand.py --mode freeze --execute
