#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --name P094_R0_p022c_dependency_gate \
  --note "P094 R0: fail closed until P022C produces machine-readable actual packed/masterless low-shadow evidence and a residual-need signature; expected HOLD is exit 8" || exit $?
exec "$python_bin" scripts/runlog.py --name P094_R0_p022c_dependency_gate -- \
  "$python_bin" scripts/diag_p094_dependency_gate.py \
  --evidence runs/evidence/P022C_shadow_storage.json
