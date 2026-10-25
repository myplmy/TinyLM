#!/usr/bin/env bash
# DONE 24Oct: full59875+5218, raw recount and owned cleanup closed. Command preserved.
# Recover only the previously time-held Falcon BLiMP full evaluation.
# Reuse pinned official AST, strict runtime and original UID-macro policy.
# Prior5013sec forecast is a reference, not a promised duration. Cap:600+7200sec.
# Fresh matching prepare/cost gates full. No TinyLM rerun, training or input wait.
# Model task scope is BLiMP67UID plus supplement5UID, not the whole BabyLM pipeline.
# Same source/policy, exclusive outputs, under20MB per evidence file,24Oct08:40KST.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python_bin="/home/uranus/tinyLM/data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
export TL_RUNLOG_GIT_SCOPE=codex-safe PYTHONUNBUFFERED=1
if [[ "${1:-}" == --check-only ]]; then
  exec "$python_bin" -B -X utf8 scripts/diag_p106b_babylm_window.py --check-only
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8mW_falcon_blimp_window_"$stamp" --note 'Recover the previously time-held Falcon evaluation only. Same official UID macro, FP32 eager/MATH, batch8,1024context,noKV. Preparation and cost are not full scores. Fresh cost forecast must fit7200sec and24Oct08:40KST. New source, no global deadline patch, no source or model mutation.'
if [[ ! -f test_result/evidence/p106b_babylm_falcon_window_v1_s1337/prepare/report.json ]]; then
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8mW_falcon_blimp_window_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_babylm_window.py --execute --mode prepare --model falcon90m --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec 600 --source-sha256 43536A20657FBACBE498B9C8B0FE2580F99866AF179EA0029A1470B5F78FFB37
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8mW_falcon_blimp_window_"$stamp" --note "Preparation failed exit=$result. Cost/full NOT_RUN; not a quality result."
    exit "$result"
  fi
fi
for phase in cost full; do
  limit=600
  [[ "$phase" != full ]] || limit=7200
  "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8mW_falcon_blimp_window_"$stamp" -- "$python_bin" -B -X utf8 scripts/diag_p106b_babylm_window.py --execute --mode "$phase" --model falcon90m --deadline 2026-10-24T08:40:00+09:00 --max-wall-sec "$limit" --source-sha256 43536A20657FBACBE498B9C8B0FE2580F99866AF179EA0029A1470B5F78FFB37
  result=$?
  if [[ "$result" != 0 ]]; then
    "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8mW_falcon_blimp_window_"$stamp" --note "Stopped phase=$phase exit=$result. Inspect exact cause and partial evidence; subsequent phase NOT_RUN. No model quality0 substitution."
    exit "$result"
  fi
done
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8mW_falcon_blimp_window_"$stamp" --note 'Both model phases returned0. Accept the full result only after59875main/5218supplement,72UID, raw recount, source/data/model unchanged and owned cleanup are verified. Full BabyLM suite and matched training budget are not claimed.'
