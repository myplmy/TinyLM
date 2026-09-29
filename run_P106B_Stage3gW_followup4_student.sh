#!/usr/bin/env bash
# P106B_Stage3gW_followup4_student: approved independent/pipeline pilot, user execution only.
# Expected 0.4h; hard limit is inside the diagnostic. Exit0 functional,8 negative/HOLD,9 tool,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3gW_followup4_student.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; use a new stage to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3gW_followup4_student --num 101 --note \
  'After integration and v25 prepare: actual small research SFT4 passes, original SHA-fixed P076 parent, full-val forgetting/fixed answers and new checkpoint. At most2h. Not300M/large SFT, not verified pseudo-label truth; medium HOLD preserved. Existing HF/parent/tokenizer unchanged. New smoke is prerequisite. Never delete original outputs to force a rerun.'
"$python_bin" scripts/runlog.py --name P106B_Stage3gW_followup4_student --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3gW_followup4_student --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_repeat4_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3gW_followup4_student --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_repeat4_gate.py --check-only --mode train-followup
"$python_bin" scripts/runlog.py --name P106B_Stage3gW_followup4_student --num 101 -- \
  "$python_bin" -B -X utf8 scripts/p106b_repeat4_gate.py --execute --mode train-followup
