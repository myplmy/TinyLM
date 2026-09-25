#!/usr/bin/env bash
# P014E G0: 3 seeds x 2 rotations x FP64/FP32, model-free CPU contract (~0.1 h).
# Expect orthogonal identity PASS. Failure blocks later G1/G2; no speed or quality claim.
# No checkpoint, HF, GPU, model load, or training. User runs after current smoke PASS.
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 099 --name P014E_Stage0W_rotation_math_contract --note "Synthetic fixed rotation and g128 accounting only. FP64 max-abs 1e-10, FP32 NRMS 1e-5. Actual model/CPU wall/GPU/full-val NOT_RUN."
"$python_bin" scripts/runlog.py --num 099 --name P014E_Stage0W_rotation_math_contract -- "$python_bin" -B -X utf8 scripts/diag_p014e_rotation_contract.py --self-test
rc=$?
if [[ "$rc" -ne 0 ]]; then
    printf '[FAIL] P014E G0 rc=%s; stop before G1/G2\n' "$rc" >&2
    exit "$rc"
fi
printf '[PASS] P014E G0 synthetic contract only; inspect 099 log, do not infer deployment benefit\n'
