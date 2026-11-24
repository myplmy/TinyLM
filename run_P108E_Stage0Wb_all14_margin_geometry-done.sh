#!/usr/bin/env bash
# Native all14-layer rival gradients, normal-prefix protection and two FD scales.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108e_geometry check
fi
"$python_bin" -B -m scripts.diag_p108e_geometry check || exit $?
timeout --signal=TERM --kill-after=20s 1830s "$python_bin" -B -X utf8 scripts/runlog.py --name P108E_Stage0Wb_all14_margin_geometry --num 108 -- "$python_bin" -B -u -m scripts.diag_p108e_geometry actual
exit $?
