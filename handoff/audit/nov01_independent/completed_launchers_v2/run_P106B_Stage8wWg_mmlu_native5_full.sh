#!/usr/bin/env bash
# Official MMLU 5-shot full; v2 profile after source/registry repair.
# Same official requests, models, policy and labels; v1 GPU launchers never ran.
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
common=(--mode full --arm native5 --profile data_cache/p106b_mmlu_official_v1_20261101/profile_v2.json --profile-sha256 A2DA0A92D7B9E9264F7D558B581D50F36FA39E313FABD3152F56718C87CBCBFB)
"$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 5520s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8wWg_mmlu_native5_full -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8wWg_mmlu_native5_full --note "actual_exit=$result; full requires57 tasks/14,042 rows and independent per-item/weighted recount. Official first_n/prompt/labels unchanged, left context truncation counted. Source/CP/originals and final owned CUDA must close. No train/teacher/CP/install/download."
exit "$result"

