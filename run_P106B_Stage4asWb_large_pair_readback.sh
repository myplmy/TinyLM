#!/usr/bin/env bash
# CPU only after large pair actual tests; declared code view pairs, raw SHA and native metrics.
# Read-only inputs and fresh small report; no stdin/implicit resume/downloads.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4asWb_large_pair_readback_"$stamp" --note 'CPU only after large pair actual tests; declared code view pairs, raw SHA and native metrics.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4asWb_large_pair_readback_"$stamp" -- "$python_bin" -B -X utf8 scripts/summarize_p106b_learning_pair.py --tag p106b_binding_scale_v1_s1337 --execute
