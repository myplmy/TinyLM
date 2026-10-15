#!/usr/bin/env bash
# CPU frozen state13312 plus new addition8192, shared parent selected by earlier DEV only.
# Independent outputs. No stdin, implicit resume, source overwrite or inference answer selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4az1W_joint_decimal_corpus_"$stamp" --note 'CPU frozen state13312 plus new addition8192, shared parent selected by earlier DEV only.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4az1W_joint_decimal_corpus_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_decimal.py --mode freeze --execute
