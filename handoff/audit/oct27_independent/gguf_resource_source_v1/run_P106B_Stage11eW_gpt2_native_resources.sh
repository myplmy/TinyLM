#!/usr/bin/env bash
# New generation-only GGUF path. Existing Core6/TinyLM/HF results are preserved.
# CPU/CUDA lanes are independent; a failed lane never turns into quality PASS.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
common=(--max-wall-sec 1800 --profile handoff/audit/oct27_independent/gguf_resource_profile_v1.json --profile-sha256 61A75B5409B9D8CFA8CC097E2B0D36300375359E38C891939F53A99C98630D2A)
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_resources.py --device cuda "${common[@]}" --check-only
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11eW_gpt2_native_resources --num 101 --note 'Existing GPT2 Q4_K_M/exact b11396 libraries; new generation worker, no old Core6 Runtime/deadline invoked. Bulk512 prefill then cache-on native argmax, F32 KV/flash off/MTP off,CPU1/CUDA2. Canary16 full-vocab positions gates full4contexts fixed32 warm1/unobserved3/observed3 and natural4x64. Stream-native TTFT versus actual IPC receive wall TTFT separate. Exact native tensor/KV storage NOT_MEASURED; raw capacity/GLOBAL GPU/RSS separate. No official reevaluation/training/new300M/sourceCP writes/install/download.'
aggregate=0
for device in cuda cpu; do
    timeout --signal=TERM --kill-after=20s 1860s "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11eW_gpt2_native_resources --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gguf_resources.py --device "$device" "${common[@]}" --execute
    result=$?
    "$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage11eW_gpt2_native_resources --num 101 --note "Final device=$device exit=$result. Numeric/cache/stream correspondence before full; no semantic or benchmark adoption. Error/hold/partial results remain. Next independent device still runs after owned cleanup."
    if [[ "$result" != 0 ]]; then aggregate="$result"; fi
done
exit "$aggregate"
