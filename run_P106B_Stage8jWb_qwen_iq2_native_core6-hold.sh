#!/usr/bin/env bash
# Exact Qwen3.5-0.8B UD-IQ2_XXS, not an HF Base or another IQ2 substitute.
# NOT_RUN v1, preserved after shared shape-dependent GPT2 negative. Use v2 singleton.
# Its hybrid-state/causal/cold-clear/full-CE canary must pass independently of GPT2.
# Native quantized kernels/F32 KV differ from HF FP32/noKV; no MTP/training here.
# Canary -> measured cost -> conditional19965row full, each evidence file below20MB.
# Caps600+600+7200sec and absolute24Oct08:40KST; no input wait or silent output reuse.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/p106b_native_core6.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWb_qwen_iq2_native_core6_"$stamp" --note 'Exact338227456B Qwen3.5-0.8B-UD-IQ2_XXS.gguf native comparison. Its own hybrid-state/tokenizer/causal canary is mandatory; GPT2 results do not admit this model. Same pinned official tasks/metrics and1024context, native precision/F32 KV explicit. Costs are not full results, all19965rows/67106choices required.'
for phase in canary cost full; do
  limit=600
  [[ "$phase" != full ]] || limit=7200
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWb_qwen_iq2_native_core6_"$stamp" -- "$python_bin" -B -X utf8 scripts/p106b_native_core6.py --execute --model qwen35_08b_iq2xxs --mode "$phase" --source-sha256 A7DF5E7E81DAA0450439061903ADE2B7EF31C6C5B702A8CEDA99C252472296A8 --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit"
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWb_qwen_iq2_native_core6_"$stamp" --note "Stopped phase=$phase exit=$result. Later phase NOT_RUN; inspect exact report and partial raw. No score0 substitution, no output overwrite."
    exit "$result"
  fi
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWb_qwen_iq2_native_core6_"$stamp" --note 'Three phases returned0. Require full denominator/raw recount, hybrid-state canary, immutable model/source/engine and owned cleanup. Retain memory-query gaps and distinguish sampled peak from continuous peak; no training or checkpoint writes.'
