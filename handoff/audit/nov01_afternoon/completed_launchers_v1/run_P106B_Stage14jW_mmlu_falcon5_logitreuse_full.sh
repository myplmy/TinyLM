#!/usr/bin/env bash
# Fresh Falcon5 official scoring: fixed batch4/1024, context logit reuse, KV off.
# CPU7 and frozen contract required. Cost114 is not a benchmark; full14042 is.
# Original 1.8 multiplier plus300s/90min/120s reserve; actual deadline15:00 KST.
# Independent user authority105; preserve old evidence and all model weights.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 CUBLAS_WORKSPACE_CONFIG=:4096:8
common=(--mode full --arm falcon5 --profile data_cache/p106b_falcon_logitreuse_shots_v1_20261101/profile.json --profile-sha256 0E03E427EFB7E55ECFB42BA4640A1AC527EFDDB7835B35D951E7D1BA60BBED09)
"$eval_python" -B -X utf8 scripts/diag_p106b_falcon_logitreuse_shots.py "${common[@]}" --check-only || exit $?
timeout --signal=TERM --kill-after=20s 5580s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14jW_mmlu_falcon5_logitreuse_full -- "$eval_python" -B -X utf8 scripts/diag_p106b_falcon_logitreuse_shots.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage14jW_mmlu_falcon5_logitreuse_full --note "actual_exit=$result; official5shot fixed4/1024 FP32 MATH; cost114 and456-score/114-choice parity first; full14042 is conditional benchmark. Source/runtime/assets immutable, finalCUDA0 required. Deadline2026-11-01T15:00+09:00, no training/CP/deletion."
exit "$result"
