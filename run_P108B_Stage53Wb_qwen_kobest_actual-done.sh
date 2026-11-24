#!/usr/bin/env bash
# Official likelihood baseline;no new TinyLM intelligence/dialogue claim.
# Existing FP32 native Qwen0.6,all five KoBEST tasks4561,0shot,Math/batch1.
# Expected5-30min;new phase limit30min within the explicit night authority.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -m scripts.diag_p108b_night_kobest check
fi
"$python_bin" -B -m scripts.diag_p108b_night_kobest check || exit $?
timeout --signal=TERM --kill-after=20s 1830s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage53Wb_qwen_kobest_actual --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_night_kobest actual
exit $?
