#!/usr/bin/env bash
# New night authority. Seal reused edit-scope features and code before fitting.
# CPU only, expected under2min, hard phase limit15min; no model or checkpoint.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_scope preflight
fi
"$python_bin" -B -m scripts.diag_p108c_scope preflight || exit $?
timeout --signal=TERM --kill-after=20s 930s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage0Wa_scope_prepare_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_scope prepare
exit $?
