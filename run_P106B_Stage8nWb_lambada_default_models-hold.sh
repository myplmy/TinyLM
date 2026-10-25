#!/usr/bin/env bash
# HOLD: unused automatic chain. Use root-supervised Stage8nWc instead.
# Official LAMBADA/default, original last whole-word target, not multiple choice.
# V2 failure closure and dictionary naming only; fixed source and exclusive outputs.
# Optional explicit model names; no interactive input. Omitted names select all seven.
# Actual per-model cost and absolute deadline govern full admission, not this max sum.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1 TQDM_DISABLE=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_lambada_default.py --check-only
fi
models=("$@")
if [[ "${#models[@]}" == 0 ]]; then
  models=(falcon90m native595-q new595-broad-f native595-f qwen06 gemma270 gemma1b)
fi
for model in "${models[@]}"; do
  case "$model" in
    falcon90m|native595-q|new595-broad-f|native595-f|qwen06|gemma270|gemma1b) ;;
    *) printf 'Unknown model: %s\n' "$model" >&2; exit 2 ;;
  esac
done
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWb_lambada_default_"$stamp" --note "공식 default5153행의 전체 마지막 단어 우도와 greedy 정확도. 요청 모델=${models[*]}. 새 학습0, 기존 출력 덮기0. 모델별canary/cost/full과08:40 KST 입장 제한을 각각 확인한다."
failed=0
for model in "${models[@]}"; do
  for phase in canary cost full; do
    limit=600
    [[ "$phase" != full ]] || limit=7200
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWb_lambada_default_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_lambada_default.py --execute --model "$model" --mode "$phase" --source-sha256 A400D971EDA6609E2ECA726F0CB49D0F9373028363EE4ABC19D6A5A1B519584D --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit"
    result=$?
    if [[ "$result" != 0 ]]; then
      failed=1
      "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWb_lambada_default_"$stamp" --note "모델=$model 단계=$phase 종료=$result. 이 모델의 이후 단계는 미실행이며0점이 아니다. 다음 독립 모델은 별도 선결을 검사한다."
      break
    fi
  done
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8nWb_lambada_default_"$stamp" --note "요청 모델 순회 종료. 오류 또는 보류 표시=$failed. 모델별full5153행과독립재계수 및원천/가중치/소스불변과소유정리가닫힌것만점수로보고한다. 생략 모델은미실행이다."
exit "$failed"
