#!/usr/bin/env bash
# P106 Stage0W: CPU-only verifier/split/string-target contract, about 0.1 h; no teacher/model/GPU.
# Failure stops this gate; success is structural, not scientific quality.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 098 --name P106_Stage0W_verified_teacher_contract --note "Synthetic verified-teacher record contract only; teacher truth, license, model and SFT NOT_RUN."
"$python_bin" scripts/runlog.py --num 098 --name P106_Stage0W_verified_teacher_contract -- "$python_bin" -B -X utf8 scripts/diag_p106_verified_teacher_contract.py --self-test
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] P106_Stage0W_verified_teacher_contract rc=%s\n' "$rc" >&2
    exit "$rc"
fi
printf '[PASS] P106_Stage0W_verified_teacher_contract fixture complete; dynamic source/teacher/model evidence NOT_RUN\n'
