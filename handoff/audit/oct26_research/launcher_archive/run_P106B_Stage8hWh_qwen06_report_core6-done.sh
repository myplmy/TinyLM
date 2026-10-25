#!/usr/bin/env bash
# V3 recovery: preserve integer label-count keys; CPU replayed all192 real raw records.
# Performed24Oct: closed full19965rows/67106choices; exact command preserved in result101.
# Prior performed versions stay done, unused versions stay hold. New tag/source; same scorer.
# Full external benchmark: original Qwen3-0.6B Base weights and native tokenizer.
# Official Core6 contract unchanged; this is not matched-pretraining comparison.
# No input wait/install/download; same precision and immutable artifacts as Stage8hWa.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe TQDM_DISABLE=1 PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_external_core6.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWh_qwen06_official_core6_"$stamp" --note 'Qwen3-0.6B Base external comparison. Canary -> cost32/task -> full19965rows/67106choices; original official prompts, metrics, datasets and0shot. Cost+30percent margin must fit7200sec and24Oct08:40KST; cost scores are not full benchmark results. Raw evidence per-file below20MB; TQDM_DISABLE is display only.'
for phase in canary cost full; do
  limit=600
  [[ "$phase" != full ]] || limit=7200
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWh_qwen06_official_core6_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_external_core6.py --execute --model qwen06 --mode "$phase" --source-sha256 51678BDA69421393982C570AE36DE405566794AAEC971D6BBAF6C9925889DA2D --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit"
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWh_qwen06_official_core6_"$stamp" --note "Stopped phase=$phase exit=$result. Later phases NOT_RUN; inspect partial report and prerequisite reason."
    exit "$result"
  fi
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8hWh_qwen06_official_core6_"$stamp" --note 'All phases returned0; verify source/weights and full raw recount before reporting. No training or automatic quality/adoption claim.'
