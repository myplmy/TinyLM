#!/usr/bin/env bash
# Four global response-window writes, sameB and same original164 questions.
# About5-15min,4GiB free. Requires complete48-value library and source/CPU seal.
# No body or auxiliary optimizer here; original baseline and old edits reused.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_target_write check; fi
"$python_bin" -B -m scripts.diag_p108b_target_write check || exit $?
timeout --signal=TERM --kill-after=20s 1260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage34Wc_target_window_global --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_target_write actual
exit $?
