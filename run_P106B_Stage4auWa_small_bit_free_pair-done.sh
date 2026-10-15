#!/usr/bin/env bash
# Completed2026-10-15 raw110231 exit0; see exact result scope, no global quality promotion.
# Same actual512 questions: saved2-class head versus saved free answers; read-only model1..5, no training/CPT.
# Only after completed actual tests. No inference answer steering or stdin.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4auWa_small_bit_free_pair_"$stamp" --note 'Same actual512 questions: saved2-class head versus saved free answers; read-only model1..5, no training/CPT.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4auWa_small_bit_free_pair_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_readout.py --tag p106b_binding_aux_v1_s1337 --execute --max-wall-sec 600
