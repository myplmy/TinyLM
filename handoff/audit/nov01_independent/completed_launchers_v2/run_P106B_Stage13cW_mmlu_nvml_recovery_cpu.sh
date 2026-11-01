#!/usr/bin/env bash
# Official MMLU5-shot recovery CPU37; original0-shot evidence/source untouched.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13cW_mmlu_nvml_recovery_cpu -- "$eval_python" -B -X utf8 -m unittest scripts.test_p106b_official_mmlu scripts.test_p106b_nvml_probe scripts.test_p106b_mmlu_nvml_recovery
result=$?
if (( result != 0 )); then exit "$result"; fi
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13cW_mmlu_nvml_recovery_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_mmlu_nvml_recovery.py --mode contract --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage13cW_mmlu_nvml_recovery_cpu --note "actual_exit=$result; CPU37 and exact old profile/source/models/policies/length reuse, private monitor/output/timing bindings only. No model/GPU/training or benchmark score."
exit "$result"
