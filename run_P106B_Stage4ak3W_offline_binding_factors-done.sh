#!/usr/bin/env bash
# CPU3 then frozen feature factors. No TinyLM/Gemma forward, GPU or checkpoints.
# About0.05h, hard600sec. Do not interpret label probes as free answer/causal proof.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
stamp="$(date +%H%M%S)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak3W_offline_binding_factors_"$stamp" --note 'Offline only: requested value, first value, last value and asked-is-first classifiers with producer/SHA joins. Same fixed features; no online quality filter or base-model update.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak3W_offline_binding_factors_"$stamp" -- "$python_bin" -B -X utf8 scripts/test_p106b_binding_factor_probe.py
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage4ak3W_offline_binding_factors_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_binding_factor_probe.py --execute --max-wall-sec 600
