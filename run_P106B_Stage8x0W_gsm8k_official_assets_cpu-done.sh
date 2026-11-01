#!/usr/bin/env bash
# Official GSM8K raw test/train copies and explicit source/runtime archive proof.
# CPU only; train is a fewshot prompt source, not optimizer training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_official_gsm8k scripts.test_p106b_official_archive || exit $?
timeout --signal=TERM --kill-after=20s 1000s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8x0W_gsm8k_official_assets_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_gsm8k.py --mode assets --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8x0W_gsm8k_official_assets_cpu --note "actual_exit=$result; pinned original test1319/train7473 and official source/runtime bytes only. Train is five-shot context, no weight updates. GPU/model/new-training/CP/install/download0. Asset proof is not a model score."
exit "$result"
