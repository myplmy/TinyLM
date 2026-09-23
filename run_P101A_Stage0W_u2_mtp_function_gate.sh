#!/usr/bin/env bash
# P101A Stage0W: E-rank/MTP tensor gate plus tiny QK-gain model gate.
# About 0.1 h CPU. This is not M0 checkpoint migration or quality evidence.
set -u -o pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage0W_u2_mtp_function_gate --note "Verify real-valued E expansion, MTP EOS targets, QK tau=1 and optimizer group. No quality or GPU claim."
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage0W_u2_mtp_function_gate -- "$python_bin" -B -X utf8 scripts/diag_p101a_math_contract.py
rc=$?
if [[ "$rc" -ne 0 ]]; then
    echo "[FAIL] P101A E/MTP math gate failed" >&2
    exit "$rc"
fi
"$python_bin" scripts/runlog.py --num 092 --name P101A_Stage0W_u2_mtp_function_gate -- "$python_bin" -B -X utf8 scripts/diag_p101a_qk_gain.py
