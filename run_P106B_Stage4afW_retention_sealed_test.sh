#!/usr/bin/env bash
# Three completed same-code arms required. Parent and three final students, code test640 each.
# About0.12h GPU; no training/checkpoint. First answers, no retries, no truth claim for public QA.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4afW_retention_sealed_test_"${stamp}" --note 'Frozen code test640 per endpoint. Same FP32 math/cacheON/nativeK1/greedy64. Count exact code values and four-view consistency, compare native loss; neither technical completion nor teacher text agreement proves general intelligence.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4afW_retention_sealed_test_"${stamp}" -- "$python_bin" -B -X utf8 scripts/diag_p106b_retention_course.py --mode evaluate --execute --max-wall-sec 1200
