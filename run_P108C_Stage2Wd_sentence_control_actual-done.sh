#!/usr/bin/env bash
#32 fresh native replies with the same frozen edit and two unchanged gates.
# Expected1-3min;no training,checkpoint save,or final-based reselection.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_sentence_control check
fi
"$python_bin" -B -m scripts.diag_p108c_sentence_control check || exit $?
timeout --signal=TERM --kill-after=20s 630s "$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage2Wd_sentence_control_actual --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_sentence_control actual
exit $?
