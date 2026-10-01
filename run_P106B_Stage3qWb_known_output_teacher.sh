#!/usr/bin/env bash
# P106B_Stage3qWb_known_output_teacher: expected 0.50h. Four code-fixed output contracts, xhigh 8192 thinking/16384 total/32768 context, maximum3 physical tries per group; teacher only.
# New stage/version only; originals preserved; every prerequisite failure stops this launcher.
# No interactive input. CPU/static success does not imply new teacher/student quality.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3qWb_known_output_teacher.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3qWb_known_output_teacher --num 101 --note 'Four code-fixed output contracts, xhigh 8192 thinking/16384 total/32768 context, maximum3 physical tries per group; teacher only. Read raw answers and report domains separately. Admission is not truth; no stdin wait.'
"$python_bin" scripts/runlog.py --name P106B_Stage3qWb_known_output_teacher --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_contract_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3qWb_known_output_teacher --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_contract_gate.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3qWb_known_output_teacher --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_contract_gate.py --execute
