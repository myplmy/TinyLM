#!/usr/bin/env bash
# Three equal-net edits, all11 official tasks, no benchmark-driven selection.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108e_official check
fi
"$python_bin" -B -m scripts.diag_p108e_official check || exit $?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108E_Stage3aW_matched_official11 --num 108 -- "$python_bin" -B -u -m scripts.diag_p108e_official actual
exit $?
