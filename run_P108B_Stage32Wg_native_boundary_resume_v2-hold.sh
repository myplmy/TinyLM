#!/usr/bin/env bash
# Actual float14 synthetic boundary protocol, nine updates and RAM-only resume.
# Original restore and two moment policies; not language quality or adoption.
# About2-10min,4GiB free. Source/config CPU preflight is a prerequisite.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_boundary_gpu check; fi
"$python_bin" -B -m scripts.diag_p108b_boundary_gpu check || exit $?
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage32Wg_native_boundary_resume_v2 --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_boundary_gpu actual
exit $?
