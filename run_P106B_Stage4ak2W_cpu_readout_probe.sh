#!/usr/bin/env bash
# Frozen capture required; CPU linear/16-wide classifiers with shuffled control.
# About0.08h, hard900sec. No TinyLM/teacher optimizer, no GPU, no product head.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak2W_cpu_readout_probe_"$stamp" --note 'Train-only normalization and dev-selected classifier; new-name code test, first-value/constant/shuffled labels controls. Classifier label accuracy is NOT TinyLM free generation or intelligence.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak2W_cpu_readout_probe_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_prefix_probe.py --mode fit --execute --max-wall-sec 900
