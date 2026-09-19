#!/usr/bin/env bash
set -u -o pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit $?
"$python_bin" scripts/runlog.py --num 083 --name P092_Stage1aT_tlinear_dst_contract \
  --note "P092 Stage1aT: actual TLinear static50/DST50 microtrainer contract; this is the trainer-wiring prerequisite, not the 30M quality run" || exit $?
exec "$python_bin" scripts/runlog.py --num 083 --name P092_Stage1aT_tlinear_dst_contract -- \
  "$python_bin" scripts/diag_dynamic_sparse_tlinear.py --steps 20 --update-every 5
