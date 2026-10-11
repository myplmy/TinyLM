#!/usr/bin/env bash
# User teacher-only after same16k capacity proof. Public family64 QA8 exactsources; size1/2/4 x thinking256/1024 two reverse orders56 logical requests/max168 attempts. No student.
# Estimated 0.75h; GPU=Y. Fresh stage, no stdin/download or automatic old-output cleanup.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
run_stamp="$(date +%H%M%S)"
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4nWb_concepts_thinking_factorial_${run_stamp}.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4nWb_concepts_thinking_factorial_"$run_stamp" --num 101 --note 'User teacher-only after same16k capacity proof. Public family64 QA8 exactsources; size1/2/4 x thinking256/1024 two reverse orders56 logical requests/max168 attempts. No student.'
"$python_bin" -B -X utf8 scripts/runlog.py --name P106B_Stage4nWb_concepts_thinking_factorial_"$run_stamp" --num 101 -- "$python_bin" -B -X utf8 scripts/diag_p106b_gemma_ac.py --mode panel --tag p106b_gemma_ac_v1_s1337 --execute --max-wall-sec 7200
