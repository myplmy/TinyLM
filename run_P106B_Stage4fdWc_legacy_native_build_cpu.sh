#!/usr/bin/env bash
# P106B_Stage4fdWc_legacy_native_build_cpu: CPU-only opt-in after successful immutable source and prefix pilot.
# Fresh root host measurement is positional, never stdin. Existing source/cache stays read-only.
# Write-once new cache only; no model/GPU/new training/download or implicit current601M addition.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
if [[ "$#" -ne 4 ]]; then
    printf '%s\n' '[HOLD] Supply four fresh root-measured arguments: free_bytes utc_timestamp storage_label evidence_json_path' >&2
    exit 8
fi
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fdWc_legacy_native_build_cpu_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
    printf '%s\n' '[STOP] Existing raw preserved; use a new stage.' >&2
    exit 8
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fdWc_legacy_native_build_cpu_"$run_stamp" --num 101 --note 'CPU-only explicit build; source/pilot/code pins and actual host plus guest disk/time budget are prerequisites. No legacy VAL access, old mutation, training, GPU, repeated-data padding, or knowledge-quality claim. Worker cap10800s; build/readback must finish before05Z with600s reserve. Raw bin/ledger stays ignored data_cache; public evidence/log below20MB.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4fdWc_legacy_native_build_cpu_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_native_expansion.py --mode build --max-wall-sec 10800 --allow-full-build --host-free-bytes "$1" --host-measured-at "$2" --host-storage-label "$3" --host-evidence-path "$4" --execute
