#!/usr/bin/env bash
# CPU only: separatev2 census counts untruncated rows, then validates <=1024 technical span candidates.
# V1 partial source/log/report preserved. No training, semantic judge, model/GPU/download or main admission.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ayWb_full_length_dolly_census_"$stamp" --note 'V2 untruncated counts plus bounded exact alignment only; Dolly source/candidates isolated. Student/GPU0. V1 failure is a census implementation error, not bad source proof.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ayWb_full_length_dolly_census_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_dolly_context_census_v2.py --execute --max-wall-sec 1200
