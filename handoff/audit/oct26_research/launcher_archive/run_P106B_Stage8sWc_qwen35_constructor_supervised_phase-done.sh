#!/usr/bin/env bash
# Performed canary only: numerical/cleanup veto9; cost and full NOT_RUN.
# V3 removes only the duplicate loader cache keyword. Original tokenizer gates remain.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1 TQDM_DISABLE=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_qwen35_text_core6.py --check-only
fi
if [[ "${TL_ROOT_EVAL_GUARD:-}" != 20261024 ]]; then
  printf '%s\n' 'HOLD8: root live supervision, actual prerequisite exit0 and owned cleanup required.'
  exit 8
fi
[[ "$#" == 1 ]] || exit 2
phase="$1"
prior=()
case "$phase" in
  canary) cap=600 ;;
  cost|full)
    [[ "${TL_PRIOR_QWEN35_EXIT0:-}" == 1 ]] || exit 8
    prior=(--prior-process-exit0)
    cap=600
    [[ "$phase" != full ]] || cap=7200
    ;;
  *) exit 2 ;;
esac
deadline=2026-10-24T08:40:00+09:00
deadline_epoch="$(date -d "$deadline" +%s)"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
/usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8sWc_qwen35_text_"$stamp" --note "One explicit phase=$phase, source2B244C6B and original text320 values/tied head; vision153/MTP15 explicitly unused. Original BPE and config33/extra13/named7 required. Official Core6 only; no training/install/download. Root actual exit/whole wall/closure/no veto/cleanup are mandatory, not report0 alone."
[[ "$?" == 0 ]] || exit 9
cap=$((cap-30))
available=$((deadline_epoch-$(date +%s)-120))
(( cap <= available )) || cap="$available"
if (( cap < 60 )); then
  printf '%s\n' 'HOLD8: no60sec phase before absolute120sec cleanup reserve; NOT_RUN not score0.'
  exit 8
fi
timeout_sec=$((cap-5))
/usr/bin/timeout --signal=INT --kill-after=5s "${timeout_sec}s" "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8sWc_qwen35_text_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_qwen35_text_core6.py --execute --mode "$phase" --source-sha256 2B244C6B576F2A03F104E5707B998B3E73546D1BD04041FAB8D83CBA49F08BD3 --deadline "$deadline" --max-wall-sec "$cap" "${prior[@]}"
result=$?
/usr/bin/timeout --signal=INT --kill-after=2s 13s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8sWc_qwen35_text_"$stamp" --note "Actual execution-runlog exit=$result. Root independent final closure/hash/no veto and whole-wall/process cleanup readback required. Timeout124/137 forbids score. No next phase executed."
[[ "$?" == 0 ]] || exit 9
exit "$result"
