#!/usr/bin/env bash
# CPU-only final exposure readback; external root exit is required for closure.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/miniforge3/envs/tlm_torch/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
helper="handoff/audit/oct26_research/run_actual_exposure.py"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 "$helper" --check-only
fi
exposure_wall_cap="$("$python_bin" -B -X utf8 -c 'import time; print(max(0, min(1120, int(1792998000-time.time()-10))))')"
if [[ ! "$exposure_wall_cap" =~ ^[0-9]+$ ]] || [[ "$exposure_wall_cap" -lt 1 ]]; then
  printf '%s\n' '[EXPERIMENT_FINAL] {"status":"AUTHORITY_HOLD","returncode":8,"models_loaded":0}'
  exit 8
fi
exec timeout --signal=TERM --kill-after=5s "${exposure_wall_cap}s" "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage10hWc_code_masked_exposure_cpu -- "$python_bin" -B -X utf8 "$helper"
