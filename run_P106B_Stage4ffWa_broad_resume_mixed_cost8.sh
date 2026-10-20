#!/usr/bin/env bash
# P106B_Stage4ffWa_broad_resume_mixed_cost8: explicit private deadline resume; original P090B and v2 payload preserved.
# No new native/SFT parent substitution, stdin, downloads, old overwrite, or semantic auto-approval.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4ffWa_broad_resume_mixed_cost8_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ffWa_broad_resume_mixed_cost8_"$run_stamp" --num 101 --note 'Private Broad v3 resume. Exact original P090B E854 parent and v2 22528 rows; v1 hash selection, mixed/staged352, token L0 and absolute native windows unchanged. Original source/globals/payload/raw stay read-only. Own bridge/outputs, same active10800/eval1200/record600 reserves. User authority ends20261021T08Z, training stop05Z; worker cap900s. Isolated five-minute idle before GPU cost. Stage completion is not semantic quality; public files below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4ffWa_broad_resume_mixed_cost8_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_broad_resume.py --mode cost --arm mixed --max-wall-sec 900 --execute
