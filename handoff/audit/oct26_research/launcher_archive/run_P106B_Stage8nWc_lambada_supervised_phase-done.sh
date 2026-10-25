#!/usr/bin/env bash
# DONE: seven models and21 phases closed; result101 section496 preserves commands.
# One root-supervised phase only. No automatic prerequisite chaining.
# Frozen LAMBADA/default A400D971, full last-word target and original5153 rows.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1 TQDM_DISABLE=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_lambada_default.py --check-only
fi
if [[ "${TL_ROOT_EVAL_GUARD:-}" != 20261024 ]]; then
  printf '%s\n' 'HOLD8: root actual prerequisite, whole-wall, process-exit and cleanup readback required.'
  exit 8
fi
[[ "$#" == 2 ]] || exit 2
model="$1"; phase="$2"
case "$model" in
  falcon90m|native595-q|new595-broad-f|native595-f|qwen06|gemma270|gemma1b) ;;
  *) exit 2 ;;
esac
case "$phase" in
  canary|cost) cap=600 ;;
  full) cap=7200 ;;
  *) exit 2 ;;
esac
deadline=2026-10-24T08:40:00+09:00
deadline_epoch="$(date -d "$deadline" +%s)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
/usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWc_lambada_supervised_"$stamp" --note "One supervised model=$model phase=$phase, original sourceA400D971 and5153 last-word targets. Root prior actual exit0 and final report/raw/source/assets/body/whole wall/owned cleanup required. Execution-runlog cap570/7170 leaves30sec note reserve; absolute reserve120sec. No automatic next phase or training/install."
[[ "$?" == 0 ]] || exit 9
cap=$((cap-30))
available=$((deadline_epoch-$(date +%s)-120))
(( cap <= available )) || cap="$available"
if (( cap < 60 )); then
  /usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWc_lambada_supervised_"$stamp" --note "HOLD8 model=$model phase=$phase, no60sec phase before absolute120sec reserve. NOT_RUN, not score0."
  [[ "$?" == 0 ]] || exit 9
  exit 8
fi
timeout_sec=$((cap-5))
/usr/bin/timeout --signal=INT --kill-after=5s "${timeout_sec}s" "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWc_lambada_supervised_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_lambada_default.py --execute --model "$model" --mode "$phase" --source-sha256 A400D971EDA6609E2ECA726F0CB49D0F9373028363EE4ABC19D6A5A1B519584D --deadline "$deadline" --max-wall-sec "$cap"
result=$?
/usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWc_lambada_supervised_"$stamp" --note "Actual execution-runlog exit=$result. Root independent whole wall/deadline and closure audit required. Timeout124/137 or incomplete cleanup forbid score and next phase. No next phase was executed here."
[[ "$?" == 0 ]] || exit 9
exit "$result"
