#!/usr/bin/env bash
# User CPU3h estimate; pinned public QA-candidate/code-format/explicit memory-turn corpus. One variant per source group, source/task caps,20MB shards. Deficit stops8 before students.
# No stdin. Existing logs/outputs preserved; new stage for retries.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4fW_capability_corpus.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4fW_capability_corpus --num 101 --note 'User CPU3h estimate; pinned public QA-candidate/code-format/explicit memory-turn corpus. One variant per source group, source/task caps,20MB shards. Deficit stops8 before students.'
"$python_bin" scripts/runlog.py --name P106B_Stage4fW_capability_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_capability_corpus.py --mode build --execute
