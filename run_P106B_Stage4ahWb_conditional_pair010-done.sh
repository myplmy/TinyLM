#!/usr/bin/env bash
# Same parent/SFT/native/pairs as beta0, contrast weight0.1. About0.25h GPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWb_conditional_pair010_"$stamp" --note 'Code-proven conditional preference beta0.1. Not a blacklist or general rejection model. Same176 updates/data/native objective as pair_zero; actual free answers and native loss are separate.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWb_conditional_pair010_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_conditional_orpo.py --mode train --arm pair010 --execute --max-wall-sec 3600
