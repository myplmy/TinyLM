#!/usr/bin/env bash
# CPU paired complete trim study only; bilingual roots sampled together, no model.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bkWb_trim_joint_pair_"$stamp" --note 'Complete trim2048 paired raw readback only, no new model or learning.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bkWb_trim_joint_pair_"$stamp" -- "$python_bin" -B -X utf8 scripts/summarize_p106b_structured_pair.py --tag p106b_joint_decimal_trim_v1_s1337 --execute
