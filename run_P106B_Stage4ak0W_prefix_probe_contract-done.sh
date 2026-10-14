#!/usr/bin/env bash
# CPU5 feature/readout contracts; synthetic model only, no checkpoint/GPU.
# About0.02h. Stop on contract failure; feature capture is a separate stage.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak0W_prefix_probe_contract_"$stamp" --note 'CPU5: no gold appended to prefix, producer labels, four-view aggregation, train-only moments, inference-hidden flag parity. Does not prove actual model quality.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak0W_prefix_probe_contract_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_prefix_probe.py
