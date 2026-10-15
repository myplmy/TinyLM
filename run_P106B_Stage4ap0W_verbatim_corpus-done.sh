#!/usr/bin/env bash
# Only complete576 verbatim teacher records: exact originals/roles/ranges/input1024 then freeze512/64, pseudo truth.
# Completed2026-10-15 raw095058 exit0;512/64 strict lossless messages and token budget.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ap0W_verbatim_corpus_"$stamp" --note 'Only complete576 verbatim teacher records: exact originals/roles/ranges/input1024 then freeze512/64, pseudo truth.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ap0W_verbatim_corpus_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_verbatim_source.py --mode corpus --execute
