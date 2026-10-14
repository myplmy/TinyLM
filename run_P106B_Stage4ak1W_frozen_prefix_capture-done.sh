#!/usr/bin/env bash
# After four-arm first-answer collection: frozen parent/replay100/pair030.
# Up to0.25h GPU, sequential subjects; base optimizer/CPT0. Stop on integrity error.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak1W_frozen_prefix_capture_"$stamp" --note 'Frozen last-prefix hidden768/projected256, actual batch1 cacheON FP32 math. Original states checked before/after. Supplied-label diagnostic, not free-answer improvement or causal proof.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak1W_frozen_prefix_capture_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_prefix_probe.py --mode capture --execute --max-wall-sec 900
