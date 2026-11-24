#!/usr/bin/env bash
# User161: full original BabyLM reading predictions; OLS remains NOT_RUN.
# Four independent frozen models; 2.2h conservative cap, not measured time.
# Source/closure errors stop the queue; ordinary model HOLD/error continues.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_CACHE_DISABLE=1
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_babylm_reading check
fi
overall=0
for model in native595-f native595-q new595-broad-f falcon90m; do
  safe_model="${model//-/_}"
  raw_name="P106B_Stage8read1Wd_${safe_model}"
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" --note 'User161 longGPU grant until2026-11-18 17KST. Existing complete Reading1726 and all original previous-word rows;original get_p/get_p2/get_logits AST;two tokenizer full CPU sweep and eight contracts;native FP32 MATH/noKV/TF32off. Three independent full-label CE oracles and real A/B/A before scalar-only exact-pair reuse. Input-only measured positions forecast;1800s internal/1860s outer+60kill,allocated8GiB/events64MB. One GPU after preceding queue closes. Official OLS/R2/AIC/pvalues NOT_RUN because statsmodels/patsy absent. No installs/downloads/new environment/training/CP changes.'
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" -- timeout --signal=INT --kill-after=60s 1860s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_babylm_reading actual --model "$model"
  result=$?
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" --note "Actual exit=$result. Read all1726 prediction rows/previous missingness/native trace,source-state-input invariance and CUDA0 before accepting collection complete. Formal OLS and training quality remain NOT_RUN."
  if [[ "$result" -eq 9 || "$result" -eq 124 || "$result" -eq 137 ]]; then exit "$result"; fi
  if [[ "$result" -ne 0 ]]; then overall=8; fi
done
exit "$overall"
