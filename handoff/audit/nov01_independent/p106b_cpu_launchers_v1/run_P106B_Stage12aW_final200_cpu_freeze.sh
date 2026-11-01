#!/usr/bin/env bash
# New FINAL200 plus disjoint DEV20; never used for learning or teacher correction.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_final_holdout || exit $?
timeout --signal=TERM --kill-after=10s 180s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage12aW_final200_cpu_freeze -- "$python_bin" -B -X utf8 scripts/diag_p106b_final_holdout.py --mode prepare --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage12aW_final200_cpu_freeze --note "actual_exit=$result; evaluation-only FINAL200/DEV20, fixed existing trained-model metadata/source. Model loading/training/GPU/quality scores NOT_RUN. No test answers to training/teacher."
exit "$result"
