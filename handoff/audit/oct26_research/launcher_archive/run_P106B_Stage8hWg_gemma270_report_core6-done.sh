#!/usr/bin/env bash
# V3 recovery: preserve integer label-count keys; CPU replayed all192 real raw records.
# Prior performed versions stay done, unused versions stay hold. New tag/source; same scorer.
# Full external benchmark, not a small-training quality judgment.
# Same pinned official Core6 tasks,0shot,FP32/eager/MATH,TF32off,KVoff,batch1.
# Canary -> task-weighted32row cost -> all19965rows/67106choices.
# Immutable model and output, no input wait, no install, internal stop24Oct08:40KST.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TQDM_DISABLE=1 PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_external_core6.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWg_gemma270_official_core6_"$stamp" --note 'Gemma3-270M Base external comparison. Same official task contract, but pretraining budget differs from TinyLM. Costs and synthetic canaries are not benchmark scores. Full phase requires cost forecast plus30percent margin to fit7200sec and08:40KST. TQDM_DISABLE changes progress display only; raw choice likelihoods are sharded below20MB.'
for phase in canary cost full; do
  limit=600
  [[ "$phase" != full ]] || limit=7200
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWg_gemma270_official_core6_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_external_core6.py --execute --model gemma270 --mode "$phase" --source-sha256 51678BDA69421393982C570AE36DE405566794AAEC971D6BBAF6C9925889DA2D --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit"
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWg_gemma270_official_core6_"$stamp" --note "Stopped phase=$phase exit=$result. Later phases NOT_RUN; inspect partial report. Prerequisite HOLD is not model quality failure."
    exit "$result"
  fi
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWg_gemma270_official_core6_"$stamp" --note 'All three phases returned0. Accept full scores only after exact row/choice counts, raw recount, source/weight immutability and cleanup evidence are verified. No model was trained.'
