#!/usr/bin/env bash
# User GPU estimate0.15h/max60min. Same16 source groups, changed task contract.
# No stdin/download/student/checkpoint writes. Exit8 HOLD/negative,9 tool error.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4iWc_trusted_task_contract16.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4iWc_trusted_task_contract16 --num 101 --note 'User GPU0.15h/max60min; new smoke first. Pinned original16/role/source, trusted SYSTEM task separated from DATA. Producer wraps learner JSON/state-turn constraints. SameGemma/MTPoff/sampler/budgets/seed; shared3 structural attempts, raw/thoughts/source/20MB preserved. No student/75M/semantic-truth PASS.'
"$python_bin" scripts/runlog.py --name P106B_Stage4iWc_trusted_task_contract16 --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_task_pilot.py --mode contract16 --execute
