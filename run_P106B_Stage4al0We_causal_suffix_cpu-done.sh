#!/usr/bin/env bash
# CPU19: after-complete-entity windows, no future answer states, row-normalized auxiliary loss.
# Independent fresh outputs; no stdin/implicit resume. Prerequisite HOLD is explicit.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0We_causal_suffix_cpu_"$stamp" --note 'CPU19: after-complete-entity windows, no future answer states, row-normalized auxiliary loss.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0We_causal_suffix_cpu_"$stamp" -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_binding_auxiliary scripts.test_p106b_binding_factor_cli
