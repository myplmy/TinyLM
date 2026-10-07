#!/usr/bin/env bash
# User GPU12h upper estimate; after exact new75M and same-SHA wire, fresh parent/micro8 accum16/ckptON four actual passes. Observe native/answers per epoch, no automatic quality PASS.
# No stdin. Existing logs/outputs preserved; new stage for retries.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4gW_capability_chat32_repeat4.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4gW_capability_chat32_repeat4 --num 101 --note 'User GPU12h upper estimate; after exact new75M and same-SHA wire, fresh parent/micro8 accum16/ckptON four actual passes. Observe native/answers per epoch, no automatic quality PASS.'
"$python_bin" scripts/runlog.py --name P106B_Stage4gW_capability_chat32_repeat4 --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_capability_corpus.py --mode train --execute
