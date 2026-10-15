#!/usr/bin/env bash
# CPU regression for fictional scale corpus, dev-only choice, indexed native windows and deadline forecasts.
# Completed 2026-10-15 CPU24; raw log094720 retained. No models or downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aq0W_large_binding_cpu_"$stamp" --note 'CPU regression for fictional scale corpus, dev-only choice, indexed native windows and deadline forecasts.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aq0W_large_binding_cpu_"$stamp" -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_binding_scale scripts.test_p106b_binding_auxiliary
