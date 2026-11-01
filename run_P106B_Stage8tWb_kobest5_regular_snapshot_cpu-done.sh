#!/usr/bin/env bash
# Prior Stage8tW rejected regular snapshot files; retain that failure/source.
# Accept exact regular snapshot or in-repo blob links, never external links.
set -uo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
source scripts/shell/tinylm_env.sh
python_bin="$(tinylm_python)" || exit $?
export TL_RUNLOG_GIT_SCOPE=codex-safe TL_WANDB_AUTO=0
"$python_bin" -B -X utf8 -m unittest scripts.test_p106b_kobest_official_eval || exit $?
timeout --signal=TERM --kill-after=10s 120s "$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8tWb_kobest5_regular_snapshot_cpu -- "$python_bin" -B -X utf8 scripts/prepare_p106b_kobest_official_eval.py --execute
result=$?
"$python_bin" -B -X utf8 scripts/runlog.py --num 101 --name P106B_Stage8tWb_kobest5_regular_snapshot_cpu --note "actual_exit=$result; source v1/error1 preserved, v2 test-only assets. No install/download/GPU/model score; official task/F1 execution remains NOT_RUN."
exit "$result"
