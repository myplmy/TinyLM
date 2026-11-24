#!/usr/bin/env bash
# Four frozen global weight states, DEV-only matched decoder/seed panel.
# About40-120min,4GiB free. Saved GREEDY answers reused; no training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_evaluate check; fi
"$python_bin" -B -m scripts.diag_p108b_evaluate check || exit $?
timeout --signal=TERM --kill-after=20s 10860s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage29Wd_dev_decode_panel --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_evaluate decode
exit $?
