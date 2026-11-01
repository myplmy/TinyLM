#!/usr/bin/env bash
# Existing strict local Falcon/HFLM only; CPU8 then all0/5shot token lengths.
# AutoModel weight loading is blocked in the CPU contract; no GPU/score/training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14aW_falcon_mmlu_cpu -- "$eval_python" -B -X utf8 -m unittest scripts.test_p106b_falcon_mmlu
result=$?
if (( result != 0 )); then exit "$result"; fi
timeout --signal=TERM --kill-after=20s 1000s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14aW_falcon_mmlu_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_falcon_mmlu.py --mode contract --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14aW_falcon_mmlu_cpu --note "actual_exit=$result; CPU8, exact official HF methods/archive/runtime/model metadata and0/5shot full lengths only. AutoModel weights blocked. No GPU/model/benchmark scores/train/CP/download/install."
exit "$result"
