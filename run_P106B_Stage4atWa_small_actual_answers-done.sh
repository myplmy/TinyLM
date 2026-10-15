#!/usr/bin/env bash
# Completed2026-10-15 raw110234 exit0; see exact result scope, no global quality promotion.
# After actual small test only: complete question/answer local Markdown and small receipt; no models or truth judge.
# No stdin or overwrite. Full public-reference view remains ignored local.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4atWa_small_actual_answers_"$stamp" --note 'After actual small test only: complete question/answer local Markdown and small receipt; no models or truth judge.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4atWa_small_actual_answers_"$stamp" -- "$python_bin" -B -X utf8 scripts/view_p106b_learning_answers.py --tag p106b_binding_aux_v1_s1337 --execute
