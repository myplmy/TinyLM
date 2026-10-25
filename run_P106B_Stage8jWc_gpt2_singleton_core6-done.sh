#!/usr/bin/env bash
# DONE 2026-10-24: canary/cost complete; full held before model by measured time.
# Native v2 singleton decode; identical strict CE/prefix/future/cold oracle.
# Original v1 source/wire/failure preserved. No threshold relaxation or skipped check.
# KV persists inside a request only, fixed batch/ubatch/output1 and copied logits.
# Actual canary/cost -> conditional full19965rows/67106choices; no model training.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/p106b_native_core6.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWc_gpt2_singleton_core6_"$stamp" --note 'Native v2 source42713A9E. Fixed singleton shape, original strict numerical tests. Cost is technical, not score. Quantized CUDA/F32KV is not HF FP32/noKV. Max600/600/7200sec and24Oct08:40KST, no input wait/install/training.'
for phase in canary cost full; do
  limit=600
  [[ "$phase" != full ]] || limit=7200
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWc_gpt2_singleton_core6_"$stamp" -- "$python_bin" -B -X utf8 scripts/p106b_native_core6.py --execute --model gpt2_q4km --mode "$phase" --source-sha256 42713A9E7A181896DAD0A10D0359BFA193264D9DAEF3445A05E970404995D2AD --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit"
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWc_gpt2_singleton_core6_"$stamp" --note "Stopped phase=$phase exit=$result. Later phases NOT_RUN; preserve actual/expected/threshold, wire and cleanup. A prerequisite HOLD is not score0."
    exit "$result"
  fi
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8jWc_gpt2_singleton_core6_"$stamp" --note 'All three phases returned0. Verify full counts/raw recount/source/assets and worker cleanup before reporting. Sampled memory and gaps do not prove continuous peak/OOM safety. No model trained.'
