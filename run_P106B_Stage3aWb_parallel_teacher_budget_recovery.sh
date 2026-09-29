#!/usr/bin/env bash
# P106B_Stage3aWb_parallel_teacher_budget_recovery: user-run recovery only; original negative result is immutable.
# Expected 1.0-1.5h, hard <=2h. Exit0 functional,8 negative/HOLD,9 tool,130 interrupt.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3aWb_parallel_teacher_budget_recovery.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; never remove HF output to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3aWb_parallel_teacher_budget_recovery --num 101 --note \
  'A1 recovery: same public source, now16 question groups per language and ctx6144/output4096 for each slot. ABBA1/2/2/1 remains. Format at least12/16 in every arm, both valid-data-rate ratios over1.05, no accepted row loss, GDN/VRAM. Old v22 gate stays negative; new v26 is write-once. User GPU only, at most2h. No model quality or integration adoption claim.'
"$python_bin" scripts/runlog.py --name P106B_Stage3aWb_parallel_teacher_budget_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3aWb_parallel_teacher_budget_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_parallel_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3aWb_parallel_teacher_budget_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_parallel_gate.py --check-only --mode recovery
"$python_bin" scripts/runlog.py --name P106B_Stage3aWb_parallel_teacher_budget_recovery --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_parallel_gate.py --execute --mode recovery
