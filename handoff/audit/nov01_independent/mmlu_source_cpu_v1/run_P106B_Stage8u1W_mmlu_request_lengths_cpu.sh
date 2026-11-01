#!/usr/bin/env bash
# MMLU official first_n 0/5-shot requests and native-token length contract.
# Original task prompt/choices/targets/metrics remain fixed. CPU-only, no model.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
timeout --signal=TERM --kill-after=20s 1000s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u1W_mmlu_request_lengths_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py --mode contract --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u1W_mmlu_request_lengths_cpu --note "actual_exit=$result; 57 tasks, separate0/5-shot length and original-data contracts. Existing HFLM left context truncation is counted, every choice target kept. No GPU/model/train/CP. Full scores need matched canary/cost/source/time/8GB admission."
exit "$result"
