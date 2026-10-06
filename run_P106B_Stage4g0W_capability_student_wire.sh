#!/usr/bin/env bash
# User GPU0.10h estimate; after new75M and task quotas, original micro8 accum16 checkpoint-on two-update wire. Not full education/semantic quality.
# No stdin. Existing logs/outputs preserved; new stage for retries.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4g0W_capability_student_wire.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4g0W_capability_student_wire --num 101 --note 'User GPU0.10h estimate; after new75M and task quotas, original micro8 accum16 checkpoint-on two-update wire. Not full education/semantic quality.'
"$python_bin" scripts/runlog.py --name P106B_Stage4g0W_capability_student_wire --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_capability_corpus.py --mode wire --execute
