#!/usr/bin/env bash
# Existing native copy, synthetic documents, real optimizer/statistics cost only.
# Internal 900sec, outer 1020+20sec; deadline reserve and 8GB guard are mandatory.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"; source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 TZ=Asia/Seoul
export CUBLAS_WORKSPACE_CONFIG=:4096:8
common=(--profile handoff/audit/nov01_independent/p107_training_profile_v1.json --profile-sha256 F4128969A73DA36046544CBC6DD1B601EA4DB808F1BCFCB2D54E4490DE012EAF --mode cost --max-wall-sec 900)
"$python_bin" -B -X utf8 scripts/diag_p107_adaptive_training.py "${common[@]}" --check-only
preflight=$?
if (( preflight != 0 )); then exit "$preflight"; fi
timeout --signal=TERM --kill-after=20s 1020s "$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage4bW_actual_training_cost -- "$python_bin" -B -X utf8 scripts/diag_p107_adaptive_training.py "${common[@]}" --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 107 --name P107_Stage4bW_actual_training_cost --note "actual_exit=$result; native-copy real optimizer cost; source/parent preserved, synthetic only, quality0, corpus0, disk checkpoint0. Exact observer equivalence and cleanup require report COMPLETE; timeout/resource=HOLD8, error9."
exit "$result"
