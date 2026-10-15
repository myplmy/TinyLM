#!/usr/bin/env bash
# CPU paired fixed-model roots, preserving bilingual arithmetic pairs together.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bbWb_joint_pair_readback_"$stamp" --note 'CPU complete joint raw pairing; bilingual root clustering, no model or checkpoint writes.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bbWb_joint_pair_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/summarize_p106b_structured_pair.py --tag p106b_joint_decimal_v1_s1337 --execute
