#!/usr/bin/env bash
# Same parent/SFT/native/pairs as beta0, contrast weight0.3. About0.25h GPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWc_conditional_pair030_"$stamp" --note 'Code-proven conditional preference beta0.3. Strong contrast may damage native language, so report both. Unique-answer/multiple-valid-answer collection is not penalized.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWc_conditional_pair030_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_conditional_orpo.py --mode train --arm pair030 --execute --max-wall-sec 3600
