#!/usr/bin/env bash
# Compare80 SMI/persistent-NVML pairs, idle and tiny FP32 GEMM, no model/training.
# Allocator256MiB, total180s wrapper, inherited3s query timeout, owned cleanup.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
timeout --signal=TERM --kill-after=20s 180s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13bW_nvml_idle_busy_probe -- "$python_bin" -B -X utf8 scripts/diag_p106b_nvml_probe.py --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13bW_nvml_idle_busy_probe --note "actual_exit=$result; no model/optimizer/checkpoint. Read-only NVML and tiny2048x2048 FP32 GEMM only. Need80 pairs/value/latency/source and final CUDA/owned-helper closure; no exact per-process peak or model-speed/quality claim."
exit "$result"
