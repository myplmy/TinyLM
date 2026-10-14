#!/usr/bin/env bash
# Same corpus/parent/steps as baseline, native objective weight1.0. About 0.25h GPU.
# Independent arm after cost8; all old checkpoints/data are read-only.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aeWc_native_replay100_"${stamp}" --note 'Native train CE weight1.0. Higher replay may preserve language but slow SFT. Same176 updates/native inputs; fixed epoch4 endpoint, no posthoc best-epoch substitution.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aeWc_native_replay100_"${stamp}" -- "$python_bin" -B -X utf8 scripts/diag_p106b_retention_course.py --mode train --arm replay100 --execute --max-wall-sec 3600
