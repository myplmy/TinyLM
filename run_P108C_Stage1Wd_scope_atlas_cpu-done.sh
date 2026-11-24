#!/usr/bin/env bash
# Same TRAIN151/DEV96/guard7,5 numeric classifiers for each new feature family.
# CPU only,expected under10min,30min bound. Fresh native/final quality not measured.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_scope_atlas check
fi
"$python_bin" -B -m scripts.diag_p108c_scope_atlas check || exit $?
timeout --signal=TERM --kill-after=20s 1830s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage1Wd_scope_atlas_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_scope_atlas actual
exit $?
