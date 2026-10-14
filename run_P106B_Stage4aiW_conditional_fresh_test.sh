#!/usr/bin/env bash
# Four pair arms required. Parent and students fresh640 first answers, no learning.
# About0.25h GPU. Old replay test remains development after method selection.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aiW_conditional_fresh_test_"$stamp" --note 'Fresh640 code facts after all pair arms complete. Same FP32 math/cacheON/nativeK1/greedy64, no candidate-constrained decoding. Exact values/four-view consistency/native loss separately, no general intelligence claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aiW_conditional_fresh_test_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_conditional_orpo.py --mode evaluate --execute --max-wall-sec 1200
