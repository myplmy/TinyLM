#!/usr/bin/env bash
# MMLU official test/dev copies, original source and 57-subject order only.
# CPU-only, no model, training, package changes or downloads. Fresh namespace.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_official_mmlu || exit $?
timeout --signal=TERM --kill-after=20s 1000s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u0W_mmlu_official_assets_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py --mode assets --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u0W_mmlu_official_assets_cpu --note "actual_exit=$result; official archive and14,042 test/285 dev only. Subject filter preserves rows/order. No auxiliary_train/validation, model/GPU/train/CP/install/download. Asset success is not a benchmark score."
exit "$result"
