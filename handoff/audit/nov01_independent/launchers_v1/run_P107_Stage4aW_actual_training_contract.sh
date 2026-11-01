#!/usr/bin/env bash
# CPU-only integration contracts. No original checkpoint, corpus or GPU.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TZ=Asia/Seoul
timeout --signal=TERM --kill-after=20s 300s "$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage4aW_actual_training_contract -- "$python_bin" -B -X utf8 -m unittest scripts.test_p107_adaptive_training scripts.test_p107_training_driver scripts.test_p107_adaptive_masking scripts.test_p107_adaptive_gpu_transfer
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage4aW_actual_training_contract --note "actual_exit=$result; CPU model/optimizer/policy/source/RNG boundary tests only. Original checkpoint0/corpus0/GPU0/disk checkpoint0/quality0. New GPU stages require sealed source/profile and <=8GB admission."
exit "$result"
