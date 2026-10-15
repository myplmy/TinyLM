#!/usr/bin/env bash
# Independent no-update word/native gradient and padding-cost diagnosis; no production switch.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bfW_right_padding_probe_"$stamp" --note 'First128 same word/native targets, FP32 gradient then BF16 compiled order pairs. Optimizer/CPT0; state/decimal objectives excluded. Existing frozen studies and defaults unchanged.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4bfW_right_padding_probe_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_padding_probe.py --execute --max-wall-sec 600
