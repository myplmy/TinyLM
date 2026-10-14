#!/usr/bin/env bash
# Same parent/SFT/native/pairs; beta0 control. Four passes176 updates. About0.25h GPU.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWa_conditional_pair_zero_"$stamp" --note 'Pair beta0 control; same native strength and all extra forward computation. Same micro8 accum16 seq1024 checkpointON, Adam5e-5 Muon2e-4. No MTP/world-quality claim.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ahWa_conditional_pair_zero_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_conditional_orpo.py --mode train --arm pair_zero --execute --max-wall-sec 3600
