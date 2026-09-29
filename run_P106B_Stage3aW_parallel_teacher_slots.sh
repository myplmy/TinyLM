#!/usr/bin/env bash
# P106B_Stage3aW_parallel_teacher_slots: approved independent/pipeline pilot, user execution only.
# Expected 0.9h; hard limit is inside the diagnostic. Exit0 functional,8 negative/HOLD,9 tool,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3aW_parallel_teacher_slots.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; use a new stage to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3aW_parallel_teacher_slots --num 101 --note \
  'A1: one teacher copy, single/two slot ABBA valid-data rate, active-student resource probe. At most2h. Positive requires both ratio over1.05, >=3/4 language groups, healthy VRAM/GDN. No quality/checkpoint claim. Existing HF/parent/tokenizer unchanged. New smoke is prerequisite. Never delete original outputs to force a rerun.'
"$python_bin" scripts/runlog.py --name P106B_Stage3aW_parallel_teacher_slots --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3aW_parallel_teacher_slots --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_parallel_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3aW_parallel_teacher_slots --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_parallel_gate.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3aW_parallel_teacher_slots --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_parallel_gate.py --execute
