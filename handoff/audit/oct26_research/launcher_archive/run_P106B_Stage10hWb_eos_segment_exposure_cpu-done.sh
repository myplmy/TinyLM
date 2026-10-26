#!/usr/bin/env bash
# CPU-only correction of EOS metadata handling; original run stays preserved.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/miniforge3/envs/tlm_torch/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
helper="handoff/audit/oct26_research/run_actual_exposure.py"
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 "$helper" --check-only
fi
exec timeout --signal=TERM --kill-after=5s 1120s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage10hWb_eos_segment_exposure_cpu -- "$python_bin" -B -X utf8 "$helper"
