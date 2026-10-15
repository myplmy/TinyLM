#!/usr/bin/env bash
# CPU10 proven labels, prefix causality, global denominator, RNG/zero loss and consumer1024 budget.
# Independent fresh outputs; stop on prerequisite/error. No stdin or implicit resume.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wa_binding_aux_cpu_"$stamp" --note 'CPU10 proven labels, prefix causality, global denominator, RNG/zero loss and consumer1024 budget.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4al0Wa_binding_aux_cpu_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_binding_auxiliary.py
