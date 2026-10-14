#!/usr/bin/env bash
# CPU reference-only views/global objective denominator/identity regression
# Estimated 0.02h; no stdin/download/cleanup/old overwrite; independent raw timestamp.
# Standard student: micro8 accum16 seq1024 checkpointON compiledefault.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4u0W_source_course_cpu_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4u0W_source_course_cpu_"$stamp" --num 101 --note 'CPU reference-only views/global objective denominator/identity regression. Read measured versus not-run stages, scope and final verdict. Parsed fields/literal agreement are not semantic truth. Keep source raw/model/corpus local. No protected source or old mutation.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4u0W_source_course_cpu_"$stamp" --num 101 -- "$python_bin" -B -X utf8 -m unittest scripts.test_p106b_source_course scripts.test_p106b_visible_source
