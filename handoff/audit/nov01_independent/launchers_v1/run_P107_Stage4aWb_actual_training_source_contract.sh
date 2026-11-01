#!/usr/bin/env bash
# Final CPU contract includes completed-step accounting at a budget boundary.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"; source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TZ=Asia/Seoul
timeout --signal=TERM --kill-after=20s 300s "$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage4aWb_actual_training_source_contract -- "$python_bin" -B -X utf8 -m unittest scripts.test_p107_adaptive_training scripts.test_p107_training_driver scripts.test_p107_adaptive_masking scripts.test_p107_adaptive_gpu_transfer
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage4aWb_actual_training_source_contract --note "actual_exit=$result; CPU-only full-state/observer/resource/partial accounting contracts. Original CP0/corpus0/GPU0/checkpoint files0/quality0."
exit "$result"
