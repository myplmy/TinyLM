#!/usr/bin/env bash
# Existing local Falcon90M; official KoBEST five tasks,4561 test rows.
# Same fixed native likelihood policy; no installs/downloads/training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$PWD/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_EVALUATE_OFFLINE=1
if [[ "${1:-}" == --check-only ]]; then exec "$python_bin" -B -m scripts.diag_p108b_external_kobest check; fi
"$python_bin" -B -m scripts.diag_p108b_external_kobest check || exit $?
timeout --signal=TERM --kill-after=20s 960s "$python_bin" -B -X utf8 scripts/runlog.py --name P108B_Stage36Wc_falcon_kobest_official --num 108 -- "$python_bin" -B -u -m scripts.diag_p108b_external_kobest actual
exit $?
