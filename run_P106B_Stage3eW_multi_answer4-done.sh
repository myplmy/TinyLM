#!/usr/bin/env bash
# P106B_Stage3eW_multi_answer4: approved independent/pipeline pilot, user execution only. Attempted by user on 2026-09-30; preserve the original command sequence.
# Expected 0.7h; hard limit is inside the diagnostic. Exit0 functional,8 negative/HOLD,9 tool,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3eW_multi_answer4.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Preserve existing runlog: %s; use a new stage to rerun.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3eW_multi_answer4 --num 101 --note \
  'B4 only after B2: same question four style variants, ctx12288 max8192 low. At most1h. Variants share concept/split and are not independent knowledge. No student/GPU quality adoption. Existing HF/parent/tokenizer unchanged. New smoke is prerequisite. Never delete original outputs to force a rerun.'
"$python_bin" scripts/runlog.py --name P106B_Stage3eW_multi_answer4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/test_p106b_pipeline_gates.py
"$python_bin" scripts/runlog.py --name P106B_Stage3eW_multi_answer4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_multi_answer_gate.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3eW_multi_answer4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_multi_answer_gate.py --check-only --mode answers4
"$python_bin" scripts/runlog.py --name P106B_Stage3eW_multi_answer4 --num 101 -- \
  "$python_bin" -B -X utf8 scripts/diag_p106b_multi_answer_gate.py --execute --mode answers4
