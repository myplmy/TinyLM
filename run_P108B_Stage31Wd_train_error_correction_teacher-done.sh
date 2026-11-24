#!/usr/bin/env bash
# Root-reviewed24 actual TRAIN failures and4 correct-answer controls.
# About15-45min,10GiB free; Gemma4/MTP2, no student or corpus admission.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_correction check; fi
"$python_bin" -B -m scripts.diag_p108b_correction check || exit $?
timeout --signal=TERM --kill-after=20s 2820s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage31Wd_train_error_correction_teacher --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_correction actual
exit $?
