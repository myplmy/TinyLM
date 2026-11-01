#!/usr/bin/env bash
# Before any model run, correct Korean name/numeral particles in draft v1.
# Preserve v1 inputs/source, answers and English prompts; freeze v2 separately.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_final_holdout || exit $?
timeout --signal=TERM --kill-after=10s 180s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage12aWb_final200_korean_particle_freeze -- "$python_bin" -B -X utf8 scripts/diag_p106b_final_holdout.py --mode prepare --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage12aWb_final200_korean_particle_freeze --note "actual_exit=$result; version2 input-quality repair before model observations. FINAL200/DEV20 labels/model conditions unchanged, v1 preserved. No training/GPU/teacher/CP writes."
exit "$result"
