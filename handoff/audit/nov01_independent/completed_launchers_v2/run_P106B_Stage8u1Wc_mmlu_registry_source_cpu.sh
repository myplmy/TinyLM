#!/usr/bin/env bash
# Preserve prior source/profile; use existing arm selector and clear task mapping.
# Official fields/data/shot policies unchanged. Fresh contract_v3/profile_v2.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_official_mmlu || exit $?
timeout --signal=TERM --kill-after=20s 1000s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u1Wc_mmlu_registry_source_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py --mode contract --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u1Wc_mmlu_registry_source_cpu --note "actual_exit=$result; explicit arm maps native/broad and0/5-shot. Prior source/profile and unused GPU SH remain preserved; no whitelist edit or checker relaxation. Fresh contract_v3/profile_v2, actual official requests/lengths only. GPU/train/CP0."
exit "$result"
