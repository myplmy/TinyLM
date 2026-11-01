#!/usr/bin/env bash
# Same frozen FINAL200 from the previously completed Broad704 ternary student.
# Run after the parent worker exits and releases owned CUDA memory.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
free_mib=$(/usr/lib/wsl/lib/nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits) || exit 8
if [[ ! "$free_mib" =~ ^[0-9]+$ ]] || (( free_mib * 1048576 < 8000000000 )); then
    echo '[HOLD] point query does not show 8GB free; model not opened.'
    exit 8
fi
common=(--mode evaluate --arm new595-broad-q --profile data_cache/p106b_final200_v1_20261101/manifest.json --profile-sha256 71FD255803B94F8D95C5A5461287A891919DC24BDC984957580CC122E5FFAEE9 --max-wall-sec 1800)
"$python_bin" -B -X utf8 scripts/diag_p106b_final_holdout.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 1920s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage12bWb_final200_broad_q -- "$python_bin" -B -X utf8 scripts/diag_p106b_final_holdout.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage12bWb_final200_broad_q --note "actual_exit=$result; same frozen FINAL200 first answers, no adaptive regeneration. Semantic scores await independent three-axis reading; prior training histories differ. Core/parent/source/owned CUDA cleanup require closure. New training/CP writes0."
exit "$result"
