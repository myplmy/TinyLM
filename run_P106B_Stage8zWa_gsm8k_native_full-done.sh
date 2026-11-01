#!/usr/bin/env bash
# Official GSM8K5-shot, fixed1024 context/256 greedy, no ChatML/MTP or training.
# Full1319 needs same-source8-row cost, 11:00 reserve and sampled8GB/allocator6GiB.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
free_mib=$(timeout 4s /usr/lib/wsl/lib/nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits) || exit 8
if [[ ! "$free_mib" =~ ^[0-9]+$ ]] || (( free_mib * 1048576 < 8000000000 )); then
    echo '[HOLD] point query does not show8GB free; model not opened.'
    exit 8
fi
common=(--mode full --arm native --profile data_cache/p106b_gsm8k_official_v1_20261101/profile_v2.json --profile-sha256 0EFFADD069945BEEE4739F4BCCD5D220D2348119FEA3329DBB1E0659A86A46F9)
"$eval_python" -B -X utf8 scripts/diag_p106b_official_gsm8k.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 10920s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8zWa_gsm8k_native_full -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_gsm8k.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8zWa_gsm8k_native_full --note "actual_exit=$result; original5shot/raw prompt and strict/flexible upstream filters. Cost8 is resource-only, full1319 only is benchmark. All scores/responses remain evaluation-only. source/CP/originals and final owned CUDA closure required; no train/teacher/CP/install/download."
exit "$result"
