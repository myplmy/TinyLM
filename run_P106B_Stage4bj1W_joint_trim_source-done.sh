#!/usr/bin/env bash
# CPU source-contract only; verified old corpus unchanged and independent execution metadata.
# Independent execution namespace; original producer files and defaults remain unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj1W_joint_trim_source_"$stamp" --note 'CPU source-contract only; verified old corpus unchanged and independent execution metadata.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bj1W_joint_trim_source_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_trim.py --mode freeze --execute --max-wall-sec 300
