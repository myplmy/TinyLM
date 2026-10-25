#!/usr/bin/env bash
# Performed observation only; actual exit9 cleanup veto, never Core6 admission.
# One whole runlog capped at595s plus5s kill reserve; no phase chain.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1 TQDM_DISABLE=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_qwen35_numeric_observer.py --check-only
fi
[[ "$#" == 0 ]] || exit 2
if [[ "${TL_ROOT_EVAL_GUARD:-}" != 20261024 ]]; then
  printf '%s\n' 'HOLD8: root supervision and actual prior process exit/cleanup are required.'
  exit 8
fi
deadline=2026-10-24T08:40:00+09:00
deadline_epoch="$(date -d "$deadline" +%s)"
available=$((deadline_epoch-$(date +%s)))
if (( available < 720 )); then
  printf '%s\n' 'HOLD8: full600s observation plus120s cleanup reserve cannot fit before08:40.'
  exit 8
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
exec /usr/bin/timeout --signal=INT --kill-after=5s 595s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8sWd_qwen35_numeric_observer_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_qwen35_numeric_observer.py --execute --source-sha256 0E735714D046D17F21001D79BF98BE9BA5D8C1C76962A00B4E1BECF8CECE78E7 --deadline "$deadline" --max-wall-sec 570
