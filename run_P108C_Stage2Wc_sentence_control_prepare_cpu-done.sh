#!/usr/bin/env bash
# Freeze8 manually reviewed Korean questions after the original final was opened.
# Post-result prompt-grammar control only; no blind-final or model change claim.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108c_sentence_control check
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108C_Stage2Wc_sentence_control_prepare_cpu --num 108 -- "$python_bin" -B -u -m scripts.diag_p108c_sentence_control prepare
exit $?
