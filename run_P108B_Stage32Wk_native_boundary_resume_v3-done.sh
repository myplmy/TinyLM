#!/usr/bin/env bash
# Actual float14 synthetic boundary protocol; no language-quality conclusion.
# Nine updates, two moment policies, RAM-only exact resume and original restore.
# About2-10min,4GiB free. Terminal CPU PASS and source seal are prerequisites.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_boundary_gpu check; fi
"$python_bin" -B -m scripts.diag_p108b_boundary_gpu check || exit $?
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage32Wk_native_boundary_resume_v3 --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_boundary_gpu actual
exit $?
