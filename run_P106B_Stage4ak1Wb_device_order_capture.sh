#!/usr/bin/env bash
# New v2 only: move model to CUDA then freeze quant cache, actual device checks.
# Up to0.25h GPU. Frozen three subjects, sparse layer observations; optimizer/CPT0.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak1Wb_device_order_capture_"$stamp" --note 'Recover diagnostic-only CPU cache placement error in freshv2. Base states checked before/after; last-prefix/sparse-layer features are not free-answer improvement. Stop on any device/parity/integrity error.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak1Wb_device_order_capture_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_prefix_probe.py --mode capture --execute --max-wall-sec 900
