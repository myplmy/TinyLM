#!/usr/bin/env bash
# Same official0shot scoring, bounded short8/long4 scheduling; no auto batch search.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 CUBLAS_WORKSPACE_CONFIG=:4096:8
common=(--mode cost --arm falcon0 --profile data_cache/p106b_falcon_logitreuse_v1_20261101/profile.json --profile-sha256 A81C7258C81976B7CCE68C6E3E13835E4A18D22F6F3A6EB17EE0D0E640E14621)
"$eval_python" -B -X utf8 scripts/diag_p106b_falcon_logitreuse.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 720s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14fWa_mmlu_falcon0_logitreuse_cost -- "$eval_python" -B -X utf8 scripts/diag_p106b_falcon_logitreuse.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14fWa_mmlu_falcon0_logitreuse_cost --note "actual_exit=$result; resource-only114 cost/456-score parity first; full14042 only is benchmark. Fixed prompt/metric/model/FP32, fixed4/1024 with official logit reuse. Existing deadline1.8+300/120reserve,6GiB/8GB unchanged. Final ownedCUDA0/source/assets unchanged required. No training/CP."
exit "$result"
