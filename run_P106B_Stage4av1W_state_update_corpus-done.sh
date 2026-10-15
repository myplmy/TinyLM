#!/usr/bin/env bash
# Completed2026-10-15 raw105803 exit0; new13312/1600/1024, student not run.
# CPU freeze13312 fresh rows from dev-selected small student. No extra public train reuse.
# Independent namespace, no stdin, no implicit resume or old checkpoint writes.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4av1W_state_update_corpus_"$stamp" --note 'CPU freeze13312 fresh rows from dev-selected small student. No extra public train reuse.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4av1W_state_update_corpus_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_state_update_aux.py --mode freeze --execute
