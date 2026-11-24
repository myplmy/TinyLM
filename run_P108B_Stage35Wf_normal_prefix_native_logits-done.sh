#!/usr/bin/env bash
# Replay four saved states,35 native target forwards,no new generation/training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_protection_logits check; fi
"$python_bin" -B -m scripts.diag_p108b_protection_logits check || exit $?
timeout --signal=TERM --kill-after=20s 180s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage35Wf_normal_prefix_native_logits --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_protection_logits actual
exit $?
