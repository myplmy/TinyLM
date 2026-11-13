#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
PY="$(tinylm_python)"
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
"${PY}" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ft4bW_remaining_source_cpu_census --note "User109 CPU remaining-source census. Reuse original English iterator and quota profile, preserve original indices/cursor, and write technical eligibility only. No teacher, GPU, source text cleaning, admission, new download or other-session corpus access."
"${PY}" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ft4bW_remaining_source_cpu_census -- timeout --signal=TERM --kill-after=20s 3750s "${PY}" -B -X utf8 -m scripts.diag_p106b_nov05_source_census --max-wall-sec 3600 --stop-file tmp/P106B_Stage4ft4bW_CENSUS_STOP

