#!/usr/bin/env bash
# DONE: seven fixed models completed; commands and closure are preserved in result101 section493.
# GPU phases only, fixed prepared source2BB7BC8D. Root live supervision required.
# Outer timeout includes runlog preparation and closure; bounded notes are checked.
# No input waits, training, downloads, source changes or automatic score adoption.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1 TQDM_DISABLE=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_belebele.py --check-only
fi
if [[ "${TL_ROOT_EVAL_GUARD:-}" != 20261024 ]]; then
  printf '%s\n' 'HOLD8: root live supervision and actual process/cleanup/deadline validation required.'
  exit 8
fi
models=("$@")
[[ "${#models[@]}" != 0 ]] || models=(native595-q falcon90m qwen06 gemma1b gemma270 new595-broad-f native595-f)
for model in "${models[@]}"; do
  case "$model" in
    falcon90m|native595-q|new595-broad-f|native595-f|qwen06|gemma270|gemma1b) ;;
    *) exit 2 ;;
  esac
done
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
deadline=2026-10-24T08:40:00+09:00
deadline_epoch="$(date -d "$deadline" +%s)"
/usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWc_belebele_supervised_"$stamp" --note "Fixed official900KO/900EN, source2BB7BC8D and prior token-only prepare. Requested models=${models[*]}. Execution-runlog cap570/7170 leaves30sec note reserve inside600/7200; absolute reserve120sec. Root closure/report SHA/no veto/actual exit/owned cleanup required. No training or download."
[[ "$?" == 0 ]] || exit 9
phase_run() {
  local model="$1" phase="$2" limit=600 available cap timeout_sec result
  [[ "$phase" != full ]] || limit=7200
  available=$((deadline_epoch-$(date +%s)-120))
  cap=$((limit-30))
  (( cap <= available )) || cap="$available"
  if (( cap < 60 )); then
    /usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWc_belebele_supervised_"$stamp" --note "HOLD8 model=$model phase=$phase: no60sec window before absolute120sec reserve. NOT_RUN, not score0."
    [[ "$?" == 0 ]] || return 9
    return 8
  fi
  timeout_sec=$((cap-5))
  /usr/bin/timeout --signal=INT --kill-after=5s "${timeout_sec}s" "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWc_belebele_supervised_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_belebele.py --execute --model "$model" --mode "$phase" --source-sha256 2BB7BC8DD6A18465DA8A4B87B4AE3452D43F5E8B26CFD01BAC41482BF9A477FB --deadline "$deadline" --max-wall-sec "$cap"
  result=$?
  /usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWc_belebele_supervised_"$stamp" --note "model=$model phase=$phase whole execution-runlog exit=$result. Matching closure/report SHA and no veto plus root actual whole wall/process/owned cleanup remain required. Timeout124/137 is error, not score0."
  [[ "$?" == 0 ]] || return 9
  return "$result"
}
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
/usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8oWc_belebele_supervised_"$stamp" --note "Requested model phases ended; aggregate=$final. Only closed full1800/7200 may be scored. Common898 was frozen before outputs. No CI/free-conversation or training-gain claim from phase completion alone."
[[ "$?" == 0 ]] || exit 9
exit "$final"
