#!/usr/bin/env bash
# CPU16: auxiliary14 plus offline factor CLI2, no target models/cache/GPU.
# Expected parser/HOLD negatives are captured by tests, not mistaken exit0 errors.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wd_auxiliary_cli_cpu_"$stamp" --note 'CPU16 final auxiliary/CLI contracts. Expected missing-input fixtures cannot load a model and are captured locally. No old numerical report rerun or overwrite.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wd_auxiliary_cli_cpu_"$stamp" -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_binding_auxiliary scripts.test_p106b_binding_factor_cli
