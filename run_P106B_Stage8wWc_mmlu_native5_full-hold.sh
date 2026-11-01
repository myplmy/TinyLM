#!/usr/bin/env bash
# Official MMLU 5-shot full: fixed data/tasks/source and complete choices.
# Single GPU, allocator6GiB and sampled8GB guard. No learning or checkpoint writes.
# Full run requires matching cost and a deadline/cost admission; partial is not full.
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
common=(--mode full --model native595-q --shots 5 --profile data_cache/p106b_mmlu_official_v1_20261101/profile.json --profile-sha256 BAB0BA1C87627B7FEDD09080FCA7774BEC2AEA64318D300D07396A3A62D448E2)
"$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 5520s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8wWc_mmlu_native5_full -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8wWc_mmlu_native5_full --note "actual_exit=$result; full requires57 tasks and14,042 rows with independent per-item/weighted recount. Official prompt/first_n/labels unchanged, left context truncation counted. Source/CP/originals and final owned CUDA must close. No training/teacher/checkpoint/install/download."
exit "$result"

