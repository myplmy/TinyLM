#!/usr/bin/env bash
# Performed observer v4; actual exit9 preserves original cleanup veto.
# Whole runlog595s plus kill5s, internal570s, no phase chain or training.
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
exec /usr/bin/timeout --signal=INT --kill-after=5s 595s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8sWe_qwen35_workspace_observer_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_qwen35_numeric_observer.py --execute --source-sha256 2BBAAE804324A1AB2BBD54D9D251E7BC07328953335E1C3762A25F0A38C0BE43 --deadline "$deadline" --max-wall-sec 570
