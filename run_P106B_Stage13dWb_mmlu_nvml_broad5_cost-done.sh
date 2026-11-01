#!/usr/bin/env bash
# Official MMLU5 cost with validated persistent NVMLv2; original evaluator AST preserved.
# Same official requests/models/labels. Original Native5 HOLD preserved; fresh NVML output.
# Single GPU8GB guard/6GiB allocator, deadline reserve, no learning/CP writes.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
free_mib=$(/usr/lib/wsl/lib/nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits) || exit 8
if [[ ! "$free_mib" =~ ^[0-9]+$ ]] || (( free_mib * 1048576 < 8000000000 )); then
    echo '[HOLD] point query does not show8GB free; model not opened.'
    exit 8
fi
common=(--mode cost --arm broad5 --profile data_cache/p106b_mmlu_nvml_v1_20261101/profile.json --profile-sha256 98B07574C8AAFAE256E4688D2BA0E4A3F6A133865368937813E460959EA182B5)
"$eval_python" -B -X utf8 scripts/diag_p106b_mmlu_nvml_recovery.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 720s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13dWb_mmlu_nvml_broad5_cost -- "$eval_python" -B -X utf8 scripts/diag_p106b_mmlu_nvml_recovery.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13dWb_mmlu_nvml_broad5_cost --note "actual_exit=$result; cost114 rows and full-label canary only, not full benchmark scores. Official first_n/prompt/labels unchanged, left context truncation counted. Source/CP/originals and final owned CUDA must close. No train/teacher/CP/install/download."
exit "$result"

