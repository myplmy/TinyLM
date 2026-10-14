#!/usr/bin/env bash
# Same parent/A/B on previously used24 development questions; not independent test. [Completed logical stage; archive in WIP_20261014b_LAUNCHER_ARCHIVE.json.]
# Estimated0.08h; no training/checkpoint write/input/download/cleanup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4wW_source_course_dev24_${stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then printf '%s\n' '[STOP] Existing raw preserved.' >&2; exit 8; fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4wW_source_course_dev24_"$stamp" --num 101 --note 'Same original parent and completedsource students: old24 is development, not independent truth/quality. Preserve actual answers, stop reasons and fixed refs. No old modification or checkpoint save.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4wW_source_course_dev24_"$stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_source_dev24.py --execute --max-wall-sec 600
