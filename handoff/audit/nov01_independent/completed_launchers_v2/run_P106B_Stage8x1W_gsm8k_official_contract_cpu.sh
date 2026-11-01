#!/usr/bin/env bash
# Original GSM8K5-shot requests, native context lengths and official metric oracles.
# CPU-only contract; no ChatML wrapper or homemade extraction rules.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
timeout --signal=TERM --kill-after=20s 1000s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8x1W_gsm8k_official_contract_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_gsm8k.py --mode contract --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8x1W_gsm8k_official_contract_cpu --note "actual_exit=$result; official five-shot1319 request hashes, exact native768-token crop and256-generation policy, original strict/flexible metric checks. GPU/model/train/CP0. Actual scores require canary/cost/frozen source/time/8GB closure."
exit "$result"
