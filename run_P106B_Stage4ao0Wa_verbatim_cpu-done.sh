#!/usr/bin/env bash
# CPU27 verifies lossless original-message/role transport, CLI budget binding, auxiliary causal masks and accounting.
# Fresh namespace, no stdin/implicit resume/old mutation; fail closed on prerequisite.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ao0Wa_verbatim_cpu_"$stamp" --note 'CPU27 verifies lossless original-message/role transport, CLI budget binding, auxiliary causal masks and accounting.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ao0Wa_verbatim_cpu_"$stamp" -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_verbatim_source scripts.test_p106b_binding_auxiliary scripts.test_p106b_binding_factor_cli
