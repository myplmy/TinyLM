#!/usr/bin/env bash
# P106B_Stage4aWb_balanced_public_corpus: expected 0.75h. CPU global hash selection and source-family25 percent token caps; pinned public inputs, new v2 shards and explicit deficit; no model or download.
# User execution only; no interactive input. Existing logs and outputs are preserved.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")" && pwd)"
source "$repo_root/scripts/shell/tinylm_env.sh"
cd "$repo_root"
python_bin="$(tinylm_python)" || exit 9
log="test_result/101_log_$(date +%Y%m%d)_P106B_Stage4aWb_balanced_public_corpus.txt"
if [[ -e "$log" || -L "$log" ]]; then
  printf '[STOP] Existing log preserved: %s. Use a new stage to retry.\n' "$log" >&2
  exit 9
fi
"$python_bin" scripts/runlog.py --name P106B_Stage4aWb_balanced_public_corpus --num 101 --note 'CPU global hash selection and source-family25 percent token caps; pinned public inputs, new v2 shards and explicit deficit; no model or download.'
"$python_bin" scripts/runlog.py --name P106B_Stage4aWb_balanced_public_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/test_p106b_stage4_recovery.py
"$python_bin" scripts/runlog.py --name P106B_Stage4aWb_balanced_public_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_balanced_public.py --check-only
"$python_bin" scripts/runlog.py --name P106B_Stage4aWb_balanced_public_corpus --num 101 -- "$python_bin" -B -X utf8 scripts/p106b_balanced_public.py --execute
