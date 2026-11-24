#!/usr/bin/env bash
# Frozen full-response values; protected norm sweep,8 new global states.
# New Nov16 17:00KST authority; stop model work20min before expiry.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_norm_sweep check
fi
"$python_bin" -B -m scripts.diag_p108b_norm_sweep check || exit $?
timeout --signal=TERM --kill-after=20s 1920s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage39Wc_protected_norm_sweep --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_norm_sweep actual
exit $?
