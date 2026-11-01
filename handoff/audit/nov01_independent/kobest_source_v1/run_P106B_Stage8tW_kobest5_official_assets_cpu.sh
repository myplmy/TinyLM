#!/usr/bin/env bash
# Official KoBEST five test assets only; no installation, model or GPU.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_kobest_official_eval || exit $?
timeout --signal=TERM --kill-after=10s 120s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8tW_kobest5_official_assets_cpu -- "$python_bin" -B -X utf8 scripts/prepare_p106b_kobest_official_eval.py --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8tW_kobest5_official_assets_cpu --note "actual_exit=$result; five official test assets only. Official task init/F1/model scores NOT_RUN, no installs/downloads/GPU. Source/labels preserved; new dependencies require approval."
exit "$result"
