#!/usr/bin/env bash
# Actual float14 boundary protocol on synthetic inputs; not language quality.
# Nine updates, two moment policies, RAM-only exact resume and original restore.
# About2-10min,4GiB free. CPU/source preflight is a prerequisite.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_boundary_gpu check; fi
"$python_bin" -B -m scripts.diag_p108b_boundary_gpu check || exit $?
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage32Wd_native_boundary_resume --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_boundary_gpu actual
exit $?
