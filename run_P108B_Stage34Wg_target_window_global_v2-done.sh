#!/usr/bin/env bash
# Reuse first closed164 after native replay; run remaining three global writes.
# Same method/B/source; progress-only schema fix. About5-12min,4GiB free.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_target_write check; fi
"$python_bin" -B -m scripts.diag_p108b_target_write check || exit $?
timeout --signal=TERM --kill-after=20s 1260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage34Wg_target_window_global_v2 --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_target_write actual
exit $?
