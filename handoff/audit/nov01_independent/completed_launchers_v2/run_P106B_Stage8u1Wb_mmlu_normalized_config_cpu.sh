#!/usr/bin/env bash
# Preserve failed v1; compare official FewshotConfig by declared YAML fields.
# Fresh contract_v2, same original tasks/data/0-and5shot meaning. CPU only.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
eval_python=data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python
export CUDA_VISIBLE_DEVICES="" TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0 TZ=Asia/Seoul
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_official_mmlu || exit $?
timeout --signal=TERM --kill-after=20s 1000s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u1Wb_mmlu_normalized_config_cpu -- "$eval_python" -B -X utf8 scripts/diag_p106b_official_mmlu.py --mode contract --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8u1Wb_mmlu_normalized_config_cpu --note "actual_exit=$result; v1 normalization-comparison error preserved, official prompt/choice/target/fewshot declarations unchanged. New contract_v2. Full0/5shot CPU request counts/lengths only, GPU/model/train/CP0."
exit "$result"
