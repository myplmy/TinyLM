#!/usr/bin/env bash
# User158/current window; four independent frozen-model full-file tasks.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="$PWD/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export PYTHONIOENCODING=utf-8 TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export CUBLAS_WORKSPACE_CONFIG=:4096:8 CUDA_CACHE_DISABLE=1
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 USE_HUB_KERNELS=0
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 -m scripts.diag_p106b_babylm_semantics check
fi
overall=0
for model in native595-f native595-q new595-broad-f falcon90m; do
  safe_model="${model//-/_}"
  raw_name="P106B_Stage8sem1Wd_${safe_model}"
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" --note 'User158 until2026-11-17 17KST. Existing official current BabyLM COMPS91028+Entity6780;whole97808 or HOLD,author skip2703 only. Six helper/two driver contracts;whole two-tokenizer CPU sweep;original AST phrase/UID/rank,real full-label oracles. One existing model load;measured whole-shape forecast gate;1800s/8GiB,512MB event cap,shards10MB;no training/download/install/CP. Current driver owns16:40 cutoff/STOP;old expired controllers unused. Owned CUDA0/source/state unchanged and independent readback required.'
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" -- timeout --signal=INT --kill-after=60s 1860s "$python_bin" -B -u -X utf8 -m scripts.diag_p106b_babylm_semantics actual --model "$model"
  result=$?
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name "$raw_name" --note "Actual shell exit=$result. Check report,all97808 denominator,original native scores,partial NOT_RUN and owned cleanup. Cost subset is engineering only;no new training gain claim."
  if [[ "$result" -eq 9 || "$result" -eq 124 || "$result" -eq 137 ]]; then
    exit "$result"
  fi
  if [[ "$result" -ne 0 ]]; then overall=8; fi
done
exit "$overall"
