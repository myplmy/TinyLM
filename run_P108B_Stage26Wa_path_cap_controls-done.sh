#!/usr/bin/env bash
# Conditional PATH and free-NET controls; all original18 arms are reused.
# About15-40min,4GiB free. No body/value optimizer or checkpoint writes.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_policy check; fi
"$python_bin" -B -m scripts.diag_p108b_policy check || exit $?
timeout --signal=TERM --kill-after=20s 7260s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage26Wa_path_cap_controls --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_policy actual --arms SAME4_PATH SEQ4_PATH ADAPT_R4_PATH ADAPT_R4_FREE_CAP
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage26Wa_path_cap_controls --num 108 --note "Final PATH/free-cap exit=$result. PATH and NET are distinct quantities; record actual movement, saturation, early-stop, source restoration and raw answers. MAG controls use separate SELECT_MAG stages and are not repeated here."
exit "$result"
