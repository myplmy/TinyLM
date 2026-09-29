#!/usr/bin/env bash
# P106B_Stage3fW_integrated_one_update: approved independent/pipeline pilot, user execution only. Attempted by user on 2026-09-30; preserve the original command sequence.
# Expected 0.8h; hard limit is inside the diagnostic. Exit0 functional,8 negative/HOLD,9 tool,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3fW_integrated_one_update.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; use a new stage to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3fW_integrated_one_update --num 101 --note \
  'Only after current A1 speed/resource, A2 overlap, B2 and B4 format, independent C4 safety PASS. First integration uses B2 fields for resource control. One teacher two slots, durable queue, C-reader epoch1:64 replay plus64 fresh variants. Micro8 accum16 checkpoint-on, exactly one optimizer. At most2h; not4epoch/300M/formal TRAIN_READY. Existing HF/parent/tokenizer unchanged. New smoke is prerequisite. Never delete original outputs to force a rerun.'
"$python_bin" scripts/runlog.py --name P106B_Stage3fW_integrated_one_update --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3fW_integrated_one_update --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_integrated_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3fW_integrated_one_update --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_integrated_gate.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3fW_integrated_one_update --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_integrated_gate.py --execute
