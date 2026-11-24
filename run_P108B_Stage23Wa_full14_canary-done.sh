#!/usr/bin/env bash
# Full14 zero-value/gradient canary. About2min, at least4GiB free.
# Prerequisite failure stops this single dependent phase; no training or CP.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
    exec "$python_bin" -B -c 'from scripts.diag_p108b_value_library import verify; verify(); print("[CHECK_ONLY] frozen profile/source/authority verified; GPU NOT_RUN")'
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage23Wa_full14_canary --num 108 --note 'Nov16 directive140 before13KST. Same completed broad-F/FP32MATH/R1; every physical layer0-13 must preserve zero intervention loss and finite auxiliary gradient. No body/value optimizer, checkpoint, install, or official-test feedback. Read canary report and original-core/CUDA cleanup before value completion.'
timeout --signal=TERM --kill-after=20s 900s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage23Wa_full14_canary --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_value_library canary
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage23Wa_full14_canary --num 108 --note "Final canary exit=$result. This checks14-layer access/gradients and exact original core, not edited-model quality."
exit "$result"
