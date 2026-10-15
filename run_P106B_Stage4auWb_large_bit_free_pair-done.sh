#!/usr/bin/env bash
# Same actual512 questions on large pair: bit/free contingency, no new generation or training/CPT.
# Only after completed actual tests. No inference answer steering or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4auWb_large_bit_free_pair_"$stamp" --note 'Same actual512 questions on large pair: bit/free contingency, no new generation or training/CPT.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4auWb_large_bit_free_pair_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_readout.py --tag p106b_binding_scale_v1_s1337 --execute --max-wall-sec 600
