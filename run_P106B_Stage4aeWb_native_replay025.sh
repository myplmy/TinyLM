#!/usr/bin/env bash
# Same corpus/parent/steps as baseline, native objective weight0.25. About 0.25h GPU.
# Independent arm after cost8; SFT micro8 accum16 ckptON plus auxiliary native8/update.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aeWb_native_replay025_"${stamp}" --note 'Native train CE weight0.25. Same source/initial body/SFT/native schedule as weight0. Record original-language loss and code task answers separately; no automatic default adoption.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4aeWb_native_replay025_"${stamp}" -- "$python_bin" -B -X utf8 scripts/diag_p106b_retention_course.py --mode train --arm replay025 --execute --max-wall-sec 3600
