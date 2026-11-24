#!/usr/bin/env bash
# New night authority; one original model, frozen input-only scope and joint edit.
# Observe254 prefixes,127 conditional replies and2 canaries; estimate2-10min.
# Native failed replay is preserved and stops this dependent stage; no training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_native check
fi
"$python_bin" -B -m scripts.diag_p108c_native check || exit $?
timeout --signal=TERM --kill-after=20s 1230s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage1Wb_native_scope_actual --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_native actual
exit $?
