#!/usr/bin/env bash
# Existing Gemma3-270M18 native derivative/write admission only, not quality.
# About3-15min,4GiB free. One FIT question, no training or new assets.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
eval_python="./data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then exec "$eval_python" -B -m scripts.diag_p108b_hf_canary check; fi
"$eval_python" -B -m scripts.diag_p108b_hf_canary check || exit $?
timeout --signal=TERM --kill-after=20s 1860s "$eval_python" -B -X utf8 scripts/runlog.py --name P108B_Stage28Wb_hf_native18_canary --num 108 -- "$eval_python" -B -u -m scripts.diag_p108b_hf_canary actual
exit $?
