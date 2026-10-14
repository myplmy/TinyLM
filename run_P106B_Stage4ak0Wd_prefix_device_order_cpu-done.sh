#!/usr/bin/env bash
# CPU7 including non-buffer cache placement order; no real checkpoint/GPU.
# About0.02h. v1 runtime error remains preserved, v2 uses fresh outputs.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak0Wd_prefix_device_order_cpu_"$stamp" --note 'CPU7 contracts, now explicitly migrate parameters before creating ordinary-attribute quant cache. CPU test is not real CUDA proof; next stage checks actual cache devices.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak0Wd_prefix_device_order_cpu_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_prefix_probe.py
