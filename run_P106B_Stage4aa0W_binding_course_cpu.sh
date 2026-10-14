#!/usr/bin/env bash
# Code-known root target/order balance CPU3 then freeze4096/512; no models
# Approx.03h. No stdin/download/cleanup/old mutation; first answers/real targets separate.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4aa0W_binding_course_cpu_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4aa0W_binding_course_cpu_"$stamp" --num 101 --note 'Code-known root target/order balance CPU3 then freeze4096/512; no models. Read native language preservation and actual target lookup separately. Finite fictional mappings are not world knowledge or75M. Original model/data preserved.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4aa0W_binding_course_cpu_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_binding_course.py
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4aa0W_binding_course_cpu_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_course.py --mode corpus --execute
