#!/usr/bin/env bash
# P106B_Stage4fdWd_legacy_native_readback_cpu: CPU-only opt-in after successful immutable source and prefix pilot.
# Fresh root host measurement is positional, never stdin. Existing source/cache stays read-only.
# Write-once new cache only; no model/GPU/new training/download or implicit current601M addition.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fdWd_legacy_native_readback_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fdWd_legacy_native_readback_cpu_"$run_stamp" --num 101 --note 'CPU-only explicit readback; source/pilot/code pins and actual host plus guest disk/time budget are prerequisites. No legacy VAL access, old mutation, training, GPU, repeated-data padding, or knowledge-quality claim. Worker cap1800s; build/readback must finish before05Z with600s reserve. Raw bin/ledger stays ignored data_cache; public evidence/log below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fdWd_legacy_native_readback_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_expansion.py --mode readback --max-wall-sec 1800 --execute
