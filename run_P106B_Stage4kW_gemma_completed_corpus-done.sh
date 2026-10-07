#!/usr/bin/env bash
# User CPU only; exact75M train plus disjoint validation/task/source caps required before publishing new merged corpus. Base/public and teacher chunks remain immutable. Incomplete shortage is HOLD8 before output/student.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_name="P106B_Stage4kW_gemma_completed_corpus"
log="test_result/101_log_$(date +%Y%m%d)_${run_name}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4kW_gemma_completed_corpus --num 101 --note 'User CPU only; exact75M train plus disjoint validation/task/source caps required before publishing new merged corpus. Base/public and teacher chunks remain immutable. Incomplete shortage is HOLD8 before output/student.'
"$python_bin" scripts/runlog.py --name P106B_Stage4kW_gemma_completed_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_deficit_production.py --mode finalize --execute
