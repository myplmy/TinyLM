#!/usr/bin/env bash
# CPU replay of existing saved histories only. No new sampled answers, training, or CUDA.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
"$python_bin" -B -X utf8 -m scripts.test_p106b_longkv_saved || exit $?
"$python_bin" -B -X utf8 scripts/diag_p106b_longkv_saved.py --check-only || exit $?
timeout --signal=TERM --kill-after=20s 660s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage15aW_gsm8k_longkv_cpu -- "$python_bin" -B -X utf8 scripts/diag_p106b_longkv_saved.py --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage15aW_gsm8k_longkv_cpu --note "actual_exit=$result; existing Native3 saved histories only, FP32 CPU/MATH, same-history KV/rebuild. Not GPU equivalence, new generation, training, or semantic cause proof. Source/CP binding and CUDA uninitialized required."
exit "$result"
