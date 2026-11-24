#!/usr/bin/env bash
# User161: current explicit long GPU permission until 2026-11-18 17KST.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_CACHE_DISABLE=1
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_babylm_semantics_long_v3 check
fi
overall=0
for model in native595-f native595-q new595-broad-f falcon90m; do
  safe_model="${model//-/_}"
  raw_name="P106B_Stage8sem4Wd_${safe_model}"
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" --note 'User161 current explicit long GPU grant until2026-11-18 17KST. Existing full BabyLM COMPS91028+Entity6780,whole97808 or HOLD. New controller/output,closed CPU sweeps reused by exact SHA,original scorer/rank/native phrase oracles. One frozen model,FP32 MATH/noKV/TF32off;measured full forecast;14400s/8GiB/512MB events. Nov18 16:30 compute cutoff;no installs/downloads/training/CP changes. Prior two review denials preserved.'
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" -- timeout --signal=INT --kill-after=60s 14460s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_babylm_semantics_long_v3 actual --model "$model"
  result=$?
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" --note "Actual exit=$result. Formal completion requires all97808/oracles/unchanged source,state/assets/owned CUDA0 and independent whole-shard readback. Cost-only is NOT_RUN for quality."
  if [[ "$result" -eq 9 || "$result" -eq 124 || "$result" -eq 137 ]]; then exit "$result"; fi
  if [[ "$result" -ne 0 ]]; then overall=8; fi
done
exit "$overall"


