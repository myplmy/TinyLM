#!/usr/bin/env bash
# Existing strict Falcon90M/HFLM, official MMLU0/5shot, no training/CP/install.
# Single GPU8GB guard/6GiB allocator; full14042 only after matching114-cost/deadline.
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
common=(--mode cost --arm falcon5 --profile data_cache/p106b_falcon_mmlu_v2_20261101/profile.json --profile-sha256 392F8ACA01DE03018F7D299E2AAB83E59DAD33267D2BB8A4C295356C57452E78)
"$eval_python" -B -X utf8 scripts/diag_p106b_falcon_mmlu.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 720s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14bWb_mmlu_falcon5_cost -- "$eval_python" -B -X utf8 scripts/diag_p106b_falcon_mmlu.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14bWb_mmlu_falcon5_cost --note "actual_exit=$result; cost114 is resource-only, full14042 is the benchmark. Same official prompt/labels/group metric and1024-token constraint, model-specific tokenizer lengths disclosed. Actual strict HF loading/full-label canary/unchanged model+source/assets and finalCUDA0 required. No training/CP/install/download."
exit "$result"
