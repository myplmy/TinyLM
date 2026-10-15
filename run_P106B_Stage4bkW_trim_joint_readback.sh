#!/usr/bin/env bash
# Parent and fresh trim students same2048/public16/legacy8/actual state dialogues; no learning.
# Independent execution namespace; original producer files and defaults remain unchanged.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bkW_trim_joint_readback_"$stamp" --note 'Parent and fresh trim students same2048/public16/legacy8/actual state dialogues; no learning.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bkW_trim_joint_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_joint_trim.py --mode evaluate --execute --max-wall-sec 2400
