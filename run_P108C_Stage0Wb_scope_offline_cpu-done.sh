#!/usr/bin/env bash
# Reuse closed numeric artifacts. Fit scope only; cached joins are not new native inference.
# CPU only, expected under5min; original/final/official data and model weights unchanged.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_scope check
fi
"$python_bin" -B -m scripts.diag_p108c_scope check || exit $?
timeout --signal=TERM --kill-after=20s 930s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage0Wb_scope_offline_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_scope offline
exit $?
