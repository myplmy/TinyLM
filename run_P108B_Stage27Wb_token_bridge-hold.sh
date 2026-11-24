#!/usr/bin/env bash
# Frozen FIT24/DEV48 target token diagnostics; no new generation or training.
# About3-10min,4GiB free. FINAL/official test answers are not inputs.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_token_bridge check; fi
"$python_bin" -B -m scripts.diag_p108b_token_bridge check || exit $?
timeout --signal=TERM --kill-after=20s 1260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage27Wb_token_bridge --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_token_bridge actual
exit $?
