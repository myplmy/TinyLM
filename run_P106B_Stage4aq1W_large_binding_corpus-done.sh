#!/usr/bin/env bash
# Freeze67072 new rows; exact source messages and train-only native indices. No models.
# Completed2026-10-15 raw095116 exit0; data only, student training not implied.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aq1W_large_binding_corpus_"$stamp" --note 'Freeze67072 new rows; exact source messages and train-only native indices. No models.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aq1W_large_binding_corpus_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_scale.py --mode freeze --execute
