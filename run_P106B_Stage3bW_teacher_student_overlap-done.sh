#!/usr/bin/env bash
# P106B_Stage3bW_teacher_student_overlap: approved independent/pipeline pilot, user execution only. Attempted by user on 2026-09-30; preserve the original command sequence.
# Expected 0.8h; hard limit is inside the diagnostic. Exit0 functional,8 negative/HOLD,9 tool,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3bW_teacher_student_overlap.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; use a new stage to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3bW_teacher_student_overlap --num 101 --note \
  'A2: serial vs durable bounded producer/consumer, one teacher slot, student micro8 with partial up-to16-row accumulation. At most2h. True interval overlap and >=6/8 language groups required. Order/cold compile prevent causal speed claim. Existing HF/parent/tokenizer unchanged. New smoke is prerequisite. Never delete original outputs to force a rerun.'
"$python_bin" scripts/runlog.py --name P106B_Stage3bW_teacher_student_overlap --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3bW_teacher_student_overlap --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_overlap_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3bW_teacher_student_overlap --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_overlap_gate.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3bW_teacher_student_overlap --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_overlap_gate.py --execute
