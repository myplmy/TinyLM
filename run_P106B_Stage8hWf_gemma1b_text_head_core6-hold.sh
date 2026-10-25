#!/usr/bin/env bash
# V2 recovery: v1 rejected unused image special and failed to serialize loading sets.
# Prior performed v1 stays done; unused v1 stays hold. New tag/source, exact text-ID guard.
# Full external benchmark: original Gemma3-1B PT weights, not the distilled TinyLM.
# Official Core6, FP32/eager/MATH/TF32off/KVoff/batch1; pretraining unmatched.
# No interactive input or installation. Per-phase forecast and24Oct08:40KST bound.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TQDM_DISABLE=1 PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_external_core6.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWf_gemma1b_official_core6_"$stamp" --note 'Gemma3-1B PT external comparison, not student distillation. Canary ->32/task cost -> all19965rows/67106choices. Identical official task/data/prompt/aggregation contract; native tokenizer/model differ. Full forecast with30percent margin must fit7200sec and08:40KST. Cost is technical only; raw shards below20MB.'
for phase in canary cost full; do
  limit=600
  [[ "$phase" != full ]] || limit=7200
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWf_gemma1b_official_core6_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_external_core6.py --execute --model gemma1b --mode "$phase" --source-sha256 1DD733198FF56833BB3515DBE5588D0E9BCC1922A449187B7E17A471AD23FBC4 --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit"
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWf_gemma1b_official_core6_"$stamp" --note "Stopped phase=$phase exit=$result; later phases NOT_RUN, not a partial benchmark PASS."
    exit "$result"
  fi
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWf_gemma1b_official_core6_"$stamp" --note 'All phases returned0; independent raw recount and immutable source/weight checks still require readback. No training occurred.'
