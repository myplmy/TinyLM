#!/usr/bin/env bash
# GPT2 small exact Q4_K_M native comparison, not a new small-training score.
# Performed24Oct: canary numerical negative; cost/full NOT_RUN, not a model score0.
# Exact b11396 headers/libraries; official task prompts and metrics, batch1,1024context.
# Native quantized kernels/F32 KV are explicitly different from HF FP32/noKV.
# Bounded memory-query retries disclose gaps; no whole-interval peak/OOM guarantee.
# Same source canary -> cost -> full, exclusive outputs below20MB/file, no input wait.
# Caps600+600+7200sec; actual full time admitted only after measured task costs.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/p106b_native_core6.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWa_gpt2_native_core6_"$stamp" --note 'Exact112858624B GPT2 Q4_K_M through the existing b11396 engine and pinned official Core6 tasks. Native tokenizer/quantized CUDA/F32 KV, not HF FP32. Canary/cost are technical prerequisites, not benchmark results. All19965rows/67106choices required; files under20MB, absolute stop24Oct08:40KST.'
for phase in canary cost full; do
  limit=600
  [[ "$phase" != full ]] || limit=7200
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWa_gpt2_native_core6_"$stamp" -- "$python_bin" -B -X utf8 scripts/p106b_native_core6.py --execute --model gpt2_q4km --mode "$phase" --source-sha256 A7DF5E7E81DAA0450439061903ADE2B7EF31C6C5B702A8CEDA99C252472296A8 --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit"
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWa_gpt2_native_core6_"$stamp" --note "Stopped phase=$phase exit=$result. Later phase NOT_RUN; preserve report/raw/telemetry gaps. Prerequisite or backend error is not a model quality0."
    exit "$result"
  fi
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWa_gpt2_native_core6_"$stamp" --note 'Three phases returned0. Verify full counts/raw recount and model/header/library/source unchanged, owned worker return0 and cleanup before reporting scores. Observed memory samples are not continuous peak/OOM proof; no model was trained.'
