#!/usr/bin/env bash
# New explicit authority ends Nov17 08:00KST; stop new work before07:40.
# Four frozen paths,880 actual replies; own-history panel is kept separate.
# Expected5-30min, hard phase60min. No training/checkpoint writes.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_boundary check
fi
"$python_bin" -B -m scripts.diag_p108c_boundary check || exit $?
timeout --signal=TERM --kill-after=20s 3630s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage2Wb_fresh_boundary_actual --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_boundary actual
exit $?
