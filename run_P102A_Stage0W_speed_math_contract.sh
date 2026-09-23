#!/usr/bin/env bash
# P102A Stage0W: S1/S2/S3 reference loss, VJP and HT estimator.
# About 0.1 h CPU; no fused/trainer/GPU speed claim.
set -u -o pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage0W_speed_math_contract --note "S1 CE reference, S2 VJP sum, S3 HT expectation. Fused kernel and whole-step speed are NOT_RUN."
"$python_bin" scripts/runlog.py --num 093 --name P102A_Stage0W_speed_math_contract -- "$python_bin" -B -X utf8 scripts/diag_p102a_contract.py
