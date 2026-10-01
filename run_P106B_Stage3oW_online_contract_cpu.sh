#!/usr/bin/env bash
# P106B_Stage3oW_online_contract_cpu: CPU-only, read-only frozen evidence. Expected 0.05h; GPU/model0.
# No stdin wait, source rewrite, new scores, similarity or automatic effort selection.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3oW_online_contract_cpu.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3oW_online_contract_cpu --num 101 --note \
  'CPU/read-only gate. No interactive input or teacher/student loading. Shared existing3 attempts and explicit configuration checked; semantic classifier/similarity/new metric implementation remain unapproved. PASS is only this technical evidence scope.'
"$python_bin" scripts/runlog.py --name P106B_Stage3oW_online_contract_cpu --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_request_budget.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oW_online_contract_cpu --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_teacher_controls.py
"$python_bin" scripts/runlog.py --name P106B_Stage3oW_online_contract_cpu --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_saved_answers.py
