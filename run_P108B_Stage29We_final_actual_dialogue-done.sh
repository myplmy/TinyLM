#!/usr/bin/env bash
# Sealed FINAL192 plus48 followups per regime, actual model history.
# About20-60min,4GiB free. Requires frozen DEV decoder selection.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_evaluate check; fi
"$python_bin" -B -m scripts.diag_p108b_evaluate check || exit $?
timeout --signal=TERM --kill-after=20s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage29We_final_actual_dialogue --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_evaluate final
exit $?
