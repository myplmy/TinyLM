#!/usr/bin/env bash
# Reuse14 physical edits;observe logits and first-token margin transfer.
# Expected1-10min;15min hard phase.24 VJP,no persistent gradients/updates/CP.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_margin check
fi
"$python_bin" -B -m scripts.diag_p108b_margin check || exit $?
timeout --signal=TERM --kill-after=20s 930s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage50Wc_margin_actual --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_margin actual
exit $?
