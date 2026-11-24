#!/usr/bin/env bash
# Four matched-NET interpolations; fixed original-correct seven copy inputs.
# Reuse existing48 values/nullspace solver. About3-10min;4GiB free GPU.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_target_protection check; fi
"$python_bin" -B -m scripts.diag_p108b_target_protection check || exit $?
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage35Wb_normal_prefix_target_control --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_target_protection actual
exit $?
