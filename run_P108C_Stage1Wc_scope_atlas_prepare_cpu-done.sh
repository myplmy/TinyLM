#!/usr/bin/env bash
# Seal the new original-feature scope atlas; do not rerun14 global edits.
# CPU only,55 new layer/pooling families plus the frozen last13 control.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_scope_atlas preflight
fi
"$python_bin" -B -m scripts.diag_p108c_scope_atlas preflight || exit $?
timeout --signal=TERM --kill-after=20s 1830s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage1Wc_scope_atlas_prepare_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_scope_atlas prepare
exit $?
