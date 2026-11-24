#!/usr/bin/env bash
# User161: existing Bonsai2B raw logits, no installation/download/new environment.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin=/home/uranus/miniforge3/envs/tlm_torch/bin/python
export PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 CUDA_CACHE_DISABLE=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_prism_native_raw check
fi
name=P106B_Stage8pr2Wd_native_raw
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$name" --note 'User161 current longGPU grant until2026-11-18 17KST. Exact existing Bonsai2B PTQ1/Prism adfffbe;matching primary ABI/C-layout and CPU8;no stock structures. New raw248320 FP32 vectors A/B/A after memory data clear;independent FP64 normalizers/native tokenizer/constant-offset HTTP diagnosis. Original HTTP HOLD8/mass tolerance preserved;invalid old probabilities never used for formal scores. One GPU after BabyLM queue;internal compute1110s/parent1200s/outer1280s+60kill,free8GiBpoint/output64MB. No training/install/download/new environment/Git/oldfiles.'
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$name" -- timeout --signal=INT --kill-after=60s 1280s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_prism_native_raw actual
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$name" --note "Actual exit=$result;check raw vectors,independent full denominator,A/B/A,source/model/runtime hashes and reaped-owned-PID NVML closure. This canary is not a formal benchmark or a model quality gain."
exit "$result"

