#!/usr/bin/env bash
# P106B_Stage3rW_review_packet_prepare: expected 0.05h. Prepare20 portable review targets only; no GPT/local-model judging now. Exact frozen v32 SHAs, write-once private shards.
# No stdin wait, model call or original rewrite. Preparation is not semantic review.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage3rW_review_packet_prepare.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage3rW_review_packet_prepare --num 101 --note 'Prepare20 portable review targets only; no GPT/local-model judging now. Exact frozen v32 SHAs, write-once private shards. Return source-linked reviewer opinions in a future task, not TRAIN_READY.'
"$python_bin" scripts/runlog.py --name P106B_Stage3rW_review_packet_prepare --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_review_packet.py --self-test
"$python_bin" scripts/runlog.py --name P106B_Stage3rW_review_packet_prepare --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_review_packet.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage3rW_review_packet_prepare --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_review_packet.py --execute
