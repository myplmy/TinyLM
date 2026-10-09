#!/usr/bin/env bash
# User CPU0.5h estimate. Resumed exact75M train plus disjointval/language/task/source quotas required. New stage after prior incomplete HOLD; original V4 destination still write-once. No student allocated.
# User-run only; no stdin/download. Exit8 is prerequisite/partial,9 error,130 interrupted.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4kWd_resumed_completed_corpus"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4kWd_resumed_completed_corpus --num 101 --note 'User CPU0.5h estimate. Resumed exact75M train plus disjointval/language/task/source quotas required. New stage after prior incomplete HOLD; original V4 destination still write-once. No student allocated.'
"$python_bin" scripts/runlog.py --name P106B_Stage4kWd_resumed_completed_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_literal_recovery.py --mode finalize --execute
