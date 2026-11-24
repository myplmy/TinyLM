#!/usr/bin/env bash
# Existing official11 tasks, one preselected global edited state.
# About5-15min,4GiB free; original full baseline reused, no training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
eval_python="./data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$eval_python" -B -m scripts.diag_p108b_official --check-only; fi
"$eval_python" -B -m scripts.diag_p108b_official --check-only || exit $?
timeout --signal=TERM --kill-after=20s 1860s "$eval_python" -B -X utf8 scripts/runlog.py --name P108B_Stage29Wh_adaptive_official11 --num 108 -- "$eval_python" -B -u -m scripts.diag_p108b_official --execute --arm ADAPT_D4 --source-sha256 3768C97E56889EB6CBFA2AC41383C3783F92E8AF2C21D70F6EA40F9DC22EA3D6 --max-wall-sec 1800
exit $?
