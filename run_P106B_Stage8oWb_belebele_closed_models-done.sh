#!/usr/bin/env bash
# DONE CPU prepare only: model phases NOT_RUN here; new GPU entry is Stage8oWc.
# Official KO/EN900 each, same A-D label likelihood, no generation/training.
# Closure+actual process0+no veto+root supervision are required together.
# No input waits. Default models are the fixed seven; --prepare is CPU token-only.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1 TQDM_DISABLE=1
source_sha=2BB7BC8DD6A18465DA8A4B87B4AE3452D43F5E8B26CFD01BAC41482BF9A477FB
deadline=2026-10-24T08:40:00+09:00
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_belebele.py --check-only
fi
prepare=0
if [[ "${1:-}" == --prepare ]]; then
  prepare=1
  shift
  [[ "$#" == 0 ]] || exit 2
elif [[ "${TL_ROOT_EVAL_GUARD:-}" != 20261024 ]]; then
  printf '%s\n' 'HOLD8: root live supervision and actual process/cleanup/deadline validation required.'
  exit 8
fi
models=("$@")
if [[ "${#models[@]}" == 0 ]]; then
  models=(native595-q falcon90m qwen06 gemma1b gemma270 new595-broad-f native595-f)
fi
for model in "${models[@]}"; do
  case "$model" in
    falcon90m|native595-q|new595-broad-f|native595-f|qwen06|gemma270|gemma1b) ;;
    *) printf 'Unknown model: %s\n' "$model" >&2; exit 2 ;;
  esac
done
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
deadline_epoch="$(date -d "$deadline" +%s)"
phase_run() {
  local model="$1" phase="$2" cap=600 available timeout_sec result
  [[ "$phase" != full ]] || cap=7200
  available=$((deadline_epoch-$(date +%s)-60))
  (( cap <= available )) || cap="$available"
  if (( cap < 60 )); then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWb_belebele_closed_"$stamp" --note "HOLD8 model=$model phase=$phase: no60sec window before absolute cleanup reserve. NOT_RUN, not score0."
    return 8
  fi
  timeout_sec=$((cap-5))
  local args=(--execute --model "$model" --mode "$phase")
  [[ "$phase" != prepare ]] || args=(--prepare --mode prepare)
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWb_belebele_closed_"$stamp" -- /usr/bin/timeout --signal=INT --kill-after=5s "${timeout_sec}s" "$python_bin" -B -X utf8 scripts/diag_p106b_belebele.py "${args[@]}" --source-sha256 "$source_sha" --deadline "$deadline" --max-wall-sec "$cap"
  result=$?
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWb_belebele_closed_"$stamp" --note "model=$model phase=$phase actual process=$result. A stored report0 alone is insufficient: require matching phase_closure, no phase_veto, root actual deadline and cleanup audit. Timeout124/137 is error, not score0."
  return "$result"
}
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWb_belebele_closed_"$stamp" --note "Pinned source2BB7BC8D, official two JSONL only; KO/EN900,1800rows7200choices per model. Default7-model pre-output token freeze, full and common-untruncated auxiliary separated. Outer phase cap plus60sec absolute cleanup reserve; root must verify actual closure. No training/install. prepare=$prepare models=${models[*]}."
if [[ "$prepare" == 1 ]]; then
  phase_run none prepare
  exit "$?"
fi
final=0
for model in "${models[@]}"; do
  for phase in canary cost full; do
    phase_run "$model" "$phase"
    result=$?
    if [[ "$result" != 0 ]]; then
      if [[ "$result" == 8 && "$final" == 0 ]]; then final=8
      elif [[ "$result" != 8 ]]; then final=9
      fi
      break
    fi
  done
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWb_belebele_closed_"$stamp" --note "Requested model phases ended; aggregate=$final. Full score requires all1800rows/7200choices and raw recount, source/input/body invariance, phase closure and actual exit. Auxiliary common set is frozen before outputs. No confidence-interval or free-conversation claim."
exit "$final"
